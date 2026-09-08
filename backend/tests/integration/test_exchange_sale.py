"""Phase 6 integration tests: Exchange Sales — posting, inventory deduction, cancellation, bale linkage."""
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
from app.modules.exchange_sale.schemas import ExchangeSaleCreate, ExchangeSaleLineCancelRequest, ExchangeSaleLineCreate
from app.modules.exchange_sale.service import ExchangeSaleService
from app.modules.ginning_bale.schemas import GinningBaleCreate
from app.modules.ginning_bale.service import GinningBaleService
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.ginning_production.schemas import GinningProductionInputCreate, GinningProductionOrderCreate, GinningProductionOutputCreate
from app.modules.ginning_production.service import GinningProductionService
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, GinningProductType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 5", short_name="TGC5", company_type=CompanyType.GINNING)
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


@pytest_asyncio.fixture
async def customer(session: AsyncSession, ginning_company: Company) -> Counterparty:
    c = Counterparty(company_id=ginning_company.id, name="Exchange Buyer Co", counterparty_type=CounterpartyType.BUYER)
    session.add(c)
    await session.flush()
    return c


def _ctx(company_id: uuid.UUID) -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester", company_id=company_id)


@pytest_asyncio.fixture
async def completed_order_with_bale(session, ginning_company, raw_cotton_warehouse, fiber_warehouse, farmer):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    prod_svc = GinningProductionService(session)
    bale_svc = GinningBaleService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08", gross_weight_kg=Decimal("3000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000")),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)
    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("3000"))],
            outputs=[
                GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("1000")),
                GinningProductionOutputCreate(product_type=GinningProductType.SEED, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("1500")),
            ],
        ),
        ctx,
    )
    completed = await prod_svc.complete(order.id, ginning_company.id, ctx)
    bale_result = await bale_svc.create(
        ginning_company.id,
        GinningBaleCreate(production_order_id=completed.id, warehouse_id=fiber_warehouse.id, gross_weight_kg=Decimal("231"), tare_weight_kg=Decimal("6")),
        ctx,
    )
    return completed, bale_result.bale


async def test_exchange_sale_deducts_stock_and_links_bale(
    session: AsyncSession, ginning_company: Company, fiber_warehouse: Warehouse, customer: Counterparty,
    completed_order_with_bale,
):
    ctx = _ctx(ginning_company.id)
    order, bale = completed_order_with_bale
    sale_svc = ExchangeSaleService(session)

    sale = await sale_svc.create(
        ginning_company.id,
        ExchangeSaleCreate(
            warehouse_id=fiber_warehouse.id,
            sale_date="2026-09-08",
            customer_id=customer.id,
            exchange_name="Uzbekistan Republican Commodity Exchange",
            lines=[
                ExchangeSaleLineCreate(product_type=GinningProductType.FIBER, bale_id=bale.id, quantity_kg=bale.net_weight_kg, unit_price=Decimal("25000")),
                ExchangeSaleLineCreate(product_type=GinningProductType.SEED, quantity_kg=Decimal("500"), unit_price=Decimal("3000")),
            ],
        ),
        ctx,
    )
    assert sale.status.value == "ACTIVE"

    response = await sale_svc.build_response(sale)
    assert response.total_kg == bale.net_weight_kg + Decimal("500")
    assert response.total_value == bale.net_weight_kg * Decimal("25000") + Decimal("500") * Decimal("3000")

    stock_repo = StockRepository(session)
    fiber_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=fiber_warehouse.id, ginning_product_type=GinningProductType.FIBER,
    )
    assert fiber_balance == Decimal("1000") - bale.net_weight_kg
    seed_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=fiber_warehouse.id, ginning_product_type=GinningProductType.SEED,
    )
    assert seed_balance == Decimal("1000")  # 1500 - 500

    from app.modules.ginning_bale.repository import GinningBaleRepository
    bale_row = await GinningBaleRepository(session).get_by_id(bale.id)
    assert bale_row.status.value == "SOLD"
    assert bale_row.sold_reference_type == "EXCHANGE_SALE"


async def test_exchange_sale_over_quantity_blocked(
    session: AsyncSession, ginning_company: Company, fiber_warehouse: Warehouse, customer: Counterparty,
    completed_order_with_bale,
):
    ctx = _ctx(ginning_company.id)
    sale_svc = ExchangeSaleService(session)

    with pytest.raises(BusinessRuleViolationError, match="Insufficient"):
        await sale_svc.create(
            ginning_company.id,
            ExchangeSaleCreate(
                warehouse_id=fiber_warehouse.id,
                sale_date="2026-09-08",
                customer_id=customer.id,
                lines=[ExchangeSaleLineCreate(product_type=GinningProductType.SEED, quantity_kg=Decimal("99999"), unit_price=Decimal("3000"))],
            ),
            ctx,
        )


async def test_exchange_sale_cancel_line_reverses_stock_and_bale(
    session: AsyncSession, ginning_company: Company, fiber_warehouse: Warehouse, customer: Counterparty,
    completed_order_with_bale,
):
    ctx = _ctx(ginning_company.id)
    order, bale = completed_order_with_bale
    sale_svc = ExchangeSaleService(session)

    sale = await sale_svc.create(
        ginning_company.id,
        ExchangeSaleCreate(
            warehouse_id=fiber_warehouse.id,
            sale_date="2026-09-08",
            customer_id=customer.id,
            lines=[ExchangeSaleLineCreate(product_type=GinningProductType.FIBER, bale_id=bale.id, quantity_kg=bale.net_weight_kg, unit_price=Decimal("25000"))],
        ),
        ctx,
    )
    line = sale.lines[0]

    cancelled_sale = await sale_svc.cancel_line(
        sale.id, ginning_company.id, line.id,
        ExchangeSaleLineCancelRequest(quantity_kg=bale.net_weight_kg, reason="customer returned goods"),
        ctx,
    )
    assert cancelled_sale.status.value == "CANCELLED"

    stock_repo = StockRepository(session)
    fiber_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=fiber_warehouse.id, ginning_product_type=GinningProductType.FIBER,
    )
    assert fiber_balance == Decimal("1000")  # fully restored

    from app.modules.ginning_bale.repository import GinningBaleRepository
    bale_row = await GinningBaleRepository(session).get_by_id(bale.id)
    assert bale_row.status.value == "IN_STOCK"
