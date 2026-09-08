"""Phase 4 integration tests: Bale creation, uniqueness, traceability, reconciliation warning."""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError
from app.modules.company.models import Company
from app.modules.cotton_receiving.schemas import CottonReceivingCreate
from app.modules.cotton_receiving.service import CottonReceivingService
from app.modules.counterparty.models import Counterparty
from app.modules.ginning_bale.schemas import GinningBaleCreate
from app.modules.ginning_bale.service import GinningBaleService
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.ginning_production.schemas import (
    GinningProductionCancel,
    GinningProductionInputCreate,
    GinningProductionOrderCreate,
    GinningProductionOutputCreate,
)
from app.modules.ginning_production.service import GinningProductionService
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, GinningProductType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 3", short_name="TGC3", company_type=CompanyType.GINNING)
    session.add(company)
    await session.flush()
    return company


@pytest_asyncio.fixture
async def raw_cotton_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(company_id=ginning_company.id, code="WH-RAW-01", name="Raw Cotton", warehouse_type=WarehouseType.RAW_COTTON)
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def fiber_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(company_id=ginning_company.id, code="WH-FIB-01", name="Fiber Warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def farmer(session: AsyncSession, ginning_company: Company) -> Counterparty:
    f = Counterparty(company_id=ginning_company.id, name="Farmer X", counterparty_type=CounterpartyType.FARMER)
    session.add(f)
    await session.flush()
    return f


def _ctx(company_id: uuid.UUID) -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester", company_id=company_id)


@pytest_asyncio.fixture
async def completed_order(session, ginning_company, raw_cotton_warehouse, fiber_warehouse, farmer):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    prod_svc = GinningProductionService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(
            bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08",
            gross_weight_kg=Decimal("1000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000"),
        ),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)

    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("1000"))],
            outputs=[GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("300"))],
        ),
        ctx,
    )
    return await prod_svc.complete(order.id, ginning_company.id, ctx)


async def test_bale_creation_and_traceability(
    session: AsyncSession, ginning_company: Company, fiber_warehouse: Warehouse, completed_order,
):
    ctx = _ctx(ginning_company.id)
    bale_svc = GinningBaleService(session)

    result1 = await bale_svc.create(
        ginning_company.id,
        GinningBaleCreate(
            production_order_id=completed_order.id, warehouse_id=fiber_warehouse.id,
            gross_weight_kg=Decimal("231"), tare_weight_kg=Decimal("6"), grade="A",
        ),
        ctx,
    )
    assert result1.bale.net_weight_kg == Decimal("225")
    assert result1.bale.production_number == completed_order.production_number
    assert result1.reconciliation_warning is None

    result2 = await bale_svc.create(
        ginning_company.id,
        GinningBaleCreate(
            production_order_id=completed_order.id, warehouse_id=fiber_warehouse.id,
            gross_weight_kg=Decimal("229"), tare_weight_kg=Decimal("6"),
        ),
        ctx,
    )
    assert result2.bale.net_weight_kg == Decimal("223")
    assert result2.bale.bale_number != result1.bale.bale_number

    # 225 + 223 = 448 < 300? No — exceeds the 300kg fiber output -> should warn
    assert result2.reconciliation_warning is not None
    assert "exceed" in result2.reconciliation_warning


async def test_bale_requires_completed_order(
    session: AsyncSession, ginning_company: Company, raw_cotton_warehouse: Warehouse,
    fiber_warehouse: Warehouse, farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    prod_svc = GinningProductionService(session)
    bale_svc = GinningBaleService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("100"))],
            outputs=[GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("30"))],
        ),
        ctx,
    )

    with pytest.raises(BusinessRuleViolationError, match="COMPLETED"):
        await bale_svc.create(
            ginning_company.id,
            GinningBaleCreate(production_order_id=order.id, warehouse_id=fiber_warehouse.id, gross_weight_kg=Decimal("100"), tare_weight_kg=Decimal("5")),
            ctx,
        )


async def test_cannot_cancel_production_order_once_baled(
    session: AsyncSession, ginning_company: Company, fiber_warehouse: Warehouse, completed_order,
):
    ctx = _ctx(ginning_company.id)
    bale_svc = GinningBaleService(session)
    prod_svc = GinningProductionService(session)

    await bale_svc.create(
        ginning_company.id,
        GinningBaleCreate(production_order_id=completed_order.id, warehouse_id=fiber_warehouse.id, gross_weight_kg=Decimal("100"), tare_weight_kg=Decimal("5")),
        ctx,
    )

    with pytest.raises(BusinessRuleViolationError, match="bales have already been created"):
        await prod_svc.cancel(
            completed_order.id, ginning_company.id, GinningProductionCancel(reason="testing bale guard"), ctx
        )
