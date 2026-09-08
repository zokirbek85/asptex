"""
Phase 3 integration tests: Ginning Production Order.
Multi-bunt input, multi-product factual output, yield/loss calc, over-consumption
prevention, and cancellation reversal.
"""
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
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.ginning_production.schemas import (
    GinningProductionCancel,
    GinningProductionInputCreate,
    GinningProductionOrderCreate,
    GinningProductionOutputCreate,
)
from app.modules.ginning_production.service import GinningProductionService
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, GinningProductType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 2", short_name="TGC2", company_type=CompanyType.GINNING)
    session.add(company)
    await session.flush()
    return company


@pytest_asyncio.fixture
async def raw_cotton_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(
        company_id=ginning_company.id, code="WH-RAW-01", name="Raw Cotton",
        warehouse_type=WarehouseType.RAW_COTTON,
    )
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def fiber_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(
        company_id=ginning_company.id, code="WH-FIB-01", name="Fiber Warehouse",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def seed_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(
        company_id=ginning_company.id, code="WH-SEED-01", name="Seed Warehouse",
        warehouse_type=WarehouseType.FINISHED_GOODS,
    )
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


async def _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, net_kg: Decimal):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(
            bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08",
            gross_weight_kg=net_kg, tare_weight_kg=Decimal("0"), unit_price=Decimal("5000"),
        ),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)
    return bunt


async def test_full_scenario_multi_bunt_input_multi_product_output(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    fiber_warehouse: Warehouse,
    seed_warehouse: Warehouse,
    farmer: Counterparty,
):
    """Mirrors the acceptance scenario: 45,000 kg input -> fiber/seed/lint/pux/ulyuk output."""
    ctx = _ctx(ginning_company.id)
    bunt = await _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, Decimal("45000"))

    prod_svc = GinningProductionService(session)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("45000"))],
            outputs=[
                GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("14000")),
                GinningProductionOutputCreate(product_type=GinningProductType.SEED, warehouse_id=seed_warehouse.id, quantity_kg=Decimal("24000")),
                GinningProductionOutputCreate(product_type=GinningProductType.LINT, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("2000")),
                GinningProductionOutputCreate(product_type=GinningProductType.PUX, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("1500")),
                GinningProductionOutputCreate(product_type=GinningProductType.ULYUK, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("1000")),
            ],
        ),
        ctx,
    )
    assert order.status.value == "DRAFT"

    completed = await prod_svc.complete(order.id, ginning_company.id, ctx)
    assert completed.status.value == "COMPLETED"

    response = await prod_svc.build_response(completed)
    assert response.total_input_kg == Decimal("45000")
    assert response.total_output_kg == Decimal("42500")  # 14000+24000+2000+1500+1000
    assert response.diff_kg == Decimal("2500")
    assert response.yield_pct.quantize(Decimal("0.01")) == (Decimal("42500") / Decimal("45000") * 100).quantize(Decimal("0.01"))
    assert response.loss_pct.quantize(Decimal("0.01")) == (Decimal("100") - response.yield_pct).quantize(Decimal("0.01"))

    # Bunt fully consumed
    bunt_svc = GinningBuntService(session)
    remaining = await bunt_svc.get_balance(bunt, ginning_company.id)
    assert remaining == Decimal("0")

    # Fiber warehouse holds FIBER(14000) + LINT(2000) + PUX(1500) + ULYUK(1000) = 18500
    stock_repo = StockRepository(session)
    fiber_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=fiber_warehouse.id,
        ginning_product_type=GinningProductType.FIBER,
    )
    assert fiber_balance == Decimal("14000")
    seed_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=seed_warehouse.id,
        ginning_product_type=GinningProductType.SEED,
    )
    assert seed_balance == Decimal("24000")


async def test_over_consumption_blocked(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    fiber_warehouse: Warehouse,
    farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt = await _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, Decimal("1000"))

    prod_svc = GinningProductionService(session)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("5000"))],
            outputs=[GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("1000"))],
        ),
        ctx,
    )

    with pytest.raises(BusinessRuleViolationError, match="Insufficient stock"):
        await prod_svc.complete(order.id, ginning_company.id, ctx)

    # No partial postings should have occurred
    remaining = await GinningBuntService(session).get_balance(bunt, ginning_company.id)
    assert remaining == Decimal("1000")


async def test_multi_bunt_input_consumption(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    fiber_warehouse: Warehouse,
    farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt1 = await _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, Decimal("20000"))
    bunt2 = await _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, Decimal("15000"))
    bunt3 = await _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, Decimal("10000"))

    prod_svc = GinningProductionService(session)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[
                GinningProductionInputCreate(bunt_id=bunt1.id, quantity_kg=Decimal("20000")),
                GinningProductionInputCreate(bunt_id=bunt2.id, quantity_kg=Decimal("15000")),
                GinningProductionInputCreate(bunt_id=bunt3.id, quantity_kg=Decimal("10000")),
            ],
            outputs=[GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("14000"))],
        ),
        ctx,
    )
    completed = await prod_svc.complete(order.id, ginning_company.id, ctx)
    response = await prod_svc.build_response(completed)
    assert response.total_input_kg == Decimal("45000")

    bunt_svc = GinningBuntService(session)
    assert await bunt_svc.get_balance(bunt1, ginning_company.id) == Decimal("0")
    assert await bunt_svc.get_balance(bunt2, ginning_company.id) == Decimal("0")
    assert await bunt_svc.get_balance(bunt3, ginning_company.id) == Decimal("0")


async def test_cancel_completed_order_reverses_all_postings(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    fiber_warehouse: Warehouse,
    farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt = await _make_bunt_with_stock(session, ginning_company, raw_cotton_warehouse, farmer, Decimal("1000"))

    prod_svc = GinningProductionService(session)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("1000"))],
            outputs=[GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("900"))],
        ),
        ctx,
    )
    await prod_svc.complete(order.id, ginning_company.id, ctx)

    cancelled = await prod_svc.cancel(
        order.id, ginning_company.id, GinningProductionCancel(reason="testing reversal"), ctx
    )
    assert cancelled.status.value == "CANCELLED"

    bunt_svc = GinningBuntService(session)
    assert await bunt_svc.get_balance(bunt, ginning_company.id) == Decimal("1000")

    stock_repo = StockRepository(session)
    fiber_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=fiber_warehouse.id,
        ginning_product_type=GinningProductType.FIBER,
    )
    assert fiber_balance == Decimal("0")
