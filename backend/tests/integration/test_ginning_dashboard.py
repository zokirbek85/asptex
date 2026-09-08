"""Phase 9 integration tests: Ginning dashboard KPI aggregation."""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.company.models import Company
from app.modules.cotton_receiving.schemas import CottonReceivingCreate
from app.modules.cotton_receiving.service import CottonReceivingService
from app.modules.counterparty.models import Counterparty
from app.modules.farmer_settlement.schemas import FarmerPaymentCreate
from app.modules.farmer_settlement.service import FarmerSettlementService
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.ginning_dashboard.service import GinningDashboardService
from app.modules.ginning_production.schemas import GinningProductionInputCreate, GinningProductionOrderCreate, GinningProductionOutputCreate
from app.modules.ginning_production.service import GinningProductionService
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, GinningProductType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 8", short_name="TGC8", company_type=CompanyType.GINNING)
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
    f = Counterparty(company_id=ginning_company.id, name="Farmer Dash Test", counterparty_type=CounterpartyType.FARMER)
    session.add(f)
    await session.flush()
    return f


def _ctx(company_id: uuid.UUID) -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester", company_id=company_id)


async def test_dashboard_summary_reflects_full_pipeline(
    session: AsyncSession, ginning_company: Company, raw_cotton_warehouse: Warehouse,
    fiber_warehouse: Warehouse, farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    prod_svc = GinningProductionService(session)
    settlement_svc = FarmerSettlementService(session)
    dashboard_svc = GinningDashboardService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08", gross_weight_kg=Decimal("10000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000")),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)

    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("8000"))],
            outputs=[
                GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("2600")),
                GinningProductionOutputCreate(product_type=GinningProductType.SEED, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("4400")),
            ],
        ),
        ctx,
    )
    await prod_svc.complete(order.id, ginning_company.id, ctx)

    payment = await settlement_svc.create(
        ginning_company.id,
        FarmerPaymentCreate(farmer_id=farmer.id, payment_date="2026-09-09", amount=Decimal("10000000")),
        ctx,
    )
    await settlement_svc.post(payment.id, ginning_company.id, ctx)

    summary = await dashboard_svc.get_summary(ginning_company.id)
    assert summary.raw_cotton_received_kg == Decimal("10000")
    assert summary.raw_cotton_available_kg == Decimal("2000")  # 10000 received - 8000 consumed
    assert summary.raw_cotton_processed_kg == Decimal("8000")
    assert summary.fiber_produced_kg == Decimal("2600")
    assert summary.seed_produced_kg == Decimal("4400")
    assert summary.fiber_yield_pct.quantize(Decimal("0.01")) == (Decimal("2600") / Decimal("8000") * 100).quantize(Decimal("0.01"))
    assert summary.open_bunts_count == 1
    assert summary.draft_production_orders_count == 0  # it's COMPLETED

    # Receivable = 10,000 kg * 5,000 = 50,000,000; paid 10,000,000 -> payable 40,000,000
    assert summary.farmer_payable_total == Decimal("40000000")
    assert summary.farmer_paid_total == Decimal("10000000")

    trend = await dashboard_svc.get_receiving_trend(ginning_company.id)
    assert len(trend) == 1
    assert trend[0].quantity_kg == Decimal("10000")

    distribution = await dashboard_svc.get_output_distribution(ginning_company.id)
    dist_map = {d.label: d.value for d in distribution}
    assert dist_map["FIBER"] == Decimal("2600")
    assert dist_map["SEED"] == Decimal("4400")
