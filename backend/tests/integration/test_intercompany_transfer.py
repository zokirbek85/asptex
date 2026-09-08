"""Phase 5 integration tests: Intercompany transfer, Ginning -> Spinning, company isolation."""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.company.models import Company
from app.modules.cotton_receiving.schemas import CottonReceivingCreate
from app.modules.cotton_receiving.service import CottonReceivingService
from app.modules.counterparty.models import Counterparty
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.ginning_production.schemas import GinningProductionInputCreate, GinningProductionOrderCreate, GinningProductionOutputCreate
from app.modules.ginning_production.service import GinningProductionService
from app.modules.intercompany_transfer.schemas import (
    IntercompanyTransferCancel,
    IntercompanyTransferCreate,
    IntercompanyTransferLineCreate,
)
from app.modules.intercompany_transfer.service import IntercompanyTransferService
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, GinningProductType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 4", short_name="TGC4", company_type=CompanyType.GINNING)
    session.add(company)
    await session.flush()
    return company


@pytest_asyncio.fixture
async def spinning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Spinning Co", short_name="TSC", company_type=CompanyType.YARN_SPINNING)
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
async def ginning_fiber_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(company_id=ginning_company.id, code="WH-FIB-01", name="Fiber Warehouse", warehouse_type=WarehouseType.FINISHED_GOODS)
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def spinning_raw_warehouse(session: AsyncSession, spinning_company: Company) -> Warehouse:
    wh = Warehouse(company_id=spinning_company.id, code="WH-RAW-SP", name="Spinning Raw Cotton", warehouse_type=WarehouseType.RAW_COTTON)
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
async def fiber_stock_2000kg(session, ginning_company, raw_cotton_warehouse, ginning_fiber_warehouse, farmer):
    """Produces 2000kg of FIBER stock in ginning_fiber_warehouse."""
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    prod_svc = GinningProductionService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08", gross_weight_kg=Decimal("6000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000")),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("6000"))],
            outputs=[GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=ginning_fiber_warehouse.id, quantity_kg=Decimal("2000"))],
        ),
        ctx,
    )
    await prod_svc.complete(order.id, ginning_company.id, ctx)
    return order


async def test_transfer_confirm_moves_stock_across_companies(
    session: AsyncSession,
    ginning_company: Company,
    spinning_company: Company,
    ginning_fiber_warehouse: Warehouse,
    spinning_raw_warehouse: Warehouse,
    fiber_stock_2000kg,
):
    ctx = _ctx(ginning_company.id)
    transfer_svc = IntercompanyTransferService(session)

    transfer = await transfer_svc.create(
        ginning_company.id,
        IntercompanyTransferCreate(
            destination_company_id=spinning_company.id,
            source_warehouse_id=ginning_fiber_warehouse.id,
            destination_warehouse_id=spinning_raw_warehouse.id,
            product_type=GinningProductType.FIBER,
            transfer_date="2026-09-08",
            unit_price=Decimal("25000"),
            lines=[IntercompanyTransferLineCreate(quantity_kg=Decimal("800"))],
        ),
        ctx,
    )
    assert transfer.status.value == "DRAFT"
    assert transfer.total_value == Decimal("800") * Decimal("25000")

    confirmed = await transfer_svc.confirm(transfer.id, ginning_company.id, ctx)
    assert confirmed.status.value == "CONFIRMED"

    stock_repo = StockRepository(session)
    ginning_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=ginning_fiber_warehouse.id, ginning_product_type=GinningProductType.FIBER,
    )
    assert ginning_balance == Decimal("2000") - Decimal("800")  # 1200 remaining

    spinning_balance = await stock_repo.get_balance(
        company_id=spinning_company.id, warehouse_id=spinning_raw_warehouse.id,
    )
    assert spinning_balance == Decimal("800")

    # Both companies can see the transfer
    from_ginning_side = await transfer_svc.get(transfer.id, ginning_company.id)
    from_spinning_side = await transfer_svc.get(transfer.id, spinning_company.id)
    assert from_ginning_side.id == from_spinning_side.id == transfer.id


async def test_transfer_requires_ginning_source_and_spinning_destination(
    session: AsyncSession,
    ginning_company: Company,
    spinning_company: Company,
    ginning_fiber_warehouse: Warehouse,
    spinning_raw_warehouse: Warehouse,
):
    ctx = _ctx(spinning_company.id)
    transfer_svc = IntercompanyTransferService(session)

    with pytest.raises(BusinessRuleViolationError, match="GINNING company"):
        await transfer_svc.create(
            spinning_company.id,  # wrong: source must be GINNING
            IntercompanyTransferCreate(
                destination_company_id=ginning_company.id,
                source_warehouse_id=spinning_raw_warehouse.id,
                destination_warehouse_id=ginning_fiber_warehouse.id,
                product_type=GinningProductType.FIBER,
                transfer_date="2026-09-08",
                lines=[IntercompanyTransferLineCreate(quantity_kg=Decimal("100"))],
            ),
            ctx,
        )


async def test_transfer_over_quantity_blocked(
    session: AsyncSession,
    ginning_company: Company,
    spinning_company: Company,
    ginning_fiber_warehouse: Warehouse,
    spinning_raw_warehouse: Warehouse,
    fiber_stock_2000kg,
):
    ctx = _ctx(ginning_company.id)
    transfer_svc = IntercompanyTransferService(session)

    transfer = await transfer_svc.create(
        ginning_company.id,
        IntercompanyTransferCreate(
            destination_company_id=spinning_company.id,
            source_warehouse_id=ginning_fiber_warehouse.id,
            destination_warehouse_id=spinning_raw_warehouse.id,
            product_type=GinningProductType.FIBER,
            transfer_date="2026-09-08",
            lines=[IntercompanyTransferLineCreate(quantity_kg=Decimal("5000"))],  # only 2000 available
        ),
        ctx,
    )
    with pytest.raises(BusinessRuleViolationError, match="Insufficient stock"):
        await transfer_svc.confirm(transfer.id, ginning_company.id, ctx)


async def test_cancel_confirmed_transfer_reverses_both_sides(
    session: AsyncSession,
    ginning_company: Company,
    spinning_company: Company,
    ginning_fiber_warehouse: Warehouse,
    spinning_raw_warehouse: Warehouse,
    fiber_stock_2000kg,
):
    ctx = _ctx(ginning_company.id)
    transfer_svc = IntercompanyTransferService(session)

    transfer = await transfer_svc.create(
        ginning_company.id,
        IntercompanyTransferCreate(
            destination_company_id=spinning_company.id,
            source_warehouse_id=ginning_fiber_warehouse.id,
            destination_warehouse_id=spinning_raw_warehouse.id,
            product_type=GinningProductType.FIBER,
            transfer_date="2026-09-08",
            lines=[IntercompanyTransferLineCreate(quantity_kg=Decimal("500"))],
        ),
        ctx,
    )
    await transfer_svc.confirm(transfer.id, ginning_company.id, ctx)
    cancelled = await transfer_svc.cancel(
        transfer.id, ginning_company.id, IntercompanyTransferCancel(reason="testing reversal"), ctx
    )
    assert cancelled.status.value == "CANCELLED"

    stock_repo = StockRepository(session)
    ginning_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=ginning_fiber_warehouse.id, ginning_product_type=GinningProductType.FIBER,
    )
    assert ginning_balance == Decimal("2000")  # fully restored
    spinning_balance = await stock_repo.get_balance(
        company_id=spinning_company.id, warehouse_id=spinning_raw_warehouse.id,
    )
    assert spinning_balance == Decimal("0")


async def test_third_party_company_cannot_see_transfer(
    session: AsyncSession,
    ginning_company: Company,
    spinning_company: Company,
    ginning_fiber_warehouse: Warehouse,
    spinning_raw_warehouse: Warehouse,
    fiber_stock_2000kg,
):
    ctx = _ctx(ginning_company.id)
    transfer_svc = IntercompanyTransferService(session)
    other_company = Company(name="Unrelated Co", company_type=CompanyType.YARN_SPINNING)
    session.add(other_company)
    await session.flush()

    transfer = await transfer_svc.create(
        ginning_company.id,
        IntercompanyTransferCreate(
            destination_company_id=spinning_company.id,
            source_warehouse_id=ginning_fiber_warehouse.id,
            destination_warehouse_id=spinning_raw_warehouse.id,
            product_type=GinningProductType.FIBER,
            transfer_date="2026-09-08",
            lines=[IntercompanyTransferLineCreate(quantity_kg=Decimal("100"))],
        ),
        ctx,
    )
    with pytest.raises(NotFoundError):
        await transfer_svc.get(transfer.id, other_company.id)
