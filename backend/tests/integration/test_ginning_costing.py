"""Phase 8 integration tests: production costing and by-product cost allocation."""
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
from app.modules.exchange_sale.schemas import ExchangeSaleCreate, ExchangeSaleLineCreate
from app.modules.exchange_sale.service import ExchangeSaleService
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.ginning_costing.schemas import CostAllocationRequest, GinningProductionCostCreate
from app.modules.ginning_costing.service import GinningCostingService
from app.modules.ginning_production.schemas import GinningProductionInputCreate, GinningProductionOrderCreate, GinningProductionOutputCreate
from app.modules.ginning_production.service import GinningProductionService
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CostAllocationMethod, CounterpartyType, GinningCostType, GinningProductType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 7", short_name="TGC7", company_type=CompanyType.GINNING)
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
    f = Counterparty(company_id=ginning_company.id, name="Farmer Cost Test", counterparty_type=CounterpartyType.FARMER)
    session.add(f)
    await session.flush()
    return f


@pytest_asyncio.fixture
async def customer(session: AsyncSession, ginning_company: Company) -> Counterparty:
    c = Counterparty(company_id=ginning_company.id, name="Cost Test Buyer", counterparty_type=CounterpartyType.BUYER)
    session.add(c)
    await session.flush()
    return c


def _ctx(company_id: uuid.UUID) -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester", company_id=company_id)


@pytest_asyncio.fixture
async def completed_order(session, ginning_company, raw_cotton_warehouse, fiber_warehouse, farmer):
    """100,000 kg raw cotton @ 5000/kg = 500,000,000 raw material cost.
    Output: FIBER 32450, SEED 54800, LINT 4120, PUX 2900, ULYUK 1850 (mirrors spec example)."""
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    prod_svc = GinningProductionService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08", gross_weight_kg=Decimal("100000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000")),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)

    order = await prod_svc.create(
        ginning_company.id,
        GinningProductionOrderCreate(
            production_date="2026-09-08",
            inputs=[GinningProductionInputCreate(bunt_id=bunt.id, quantity_kg=Decimal("100000"))],
            outputs=[
                GinningProductionOutputCreate(product_type=GinningProductType.FIBER, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("32450")),
                GinningProductionOutputCreate(product_type=GinningProductType.SEED, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("54800")),
                GinningProductionOutputCreate(product_type=GinningProductType.LINT, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("4120")),
                GinningProductionOutputCreate(product_type=GinningProductType.PUX, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("2900")),
                GinningProductionOutputCreate(product_type=GinningProductType.ULYUK, warehouse_id=fiber_warehouse.id, quantity_kg=Decimal("1850")),
            ],
        ),
        ctx,
    )
    return await prod_svc.complete(order.id, ginning_company.id, ctx)


async def test_raw_material_cost_computed_from_farmer_price(
    session: AsyncSession, ginning_company: Company, completed_order,
):
    costing_svc = GinningCostingService(session)
    order = await costing_svc.order_repo.get_scoped_with_lines(completed_order.id, ginning_company.id)
    raw_cost = await costing_svc.compute_raw_material_cost(order)
    assert raw_cost == Decimal("100000") * Decimal("5000")  # 500,000,000


async def test_quantity_allocation(
    session: AsyncSession, ginning_company: Company, completed_order,
):
    ctx = _ctx(ginning_company.id)
    costing_svc = GinningCostingService(session)

    await costing_svc.add_cost(
        ginning_company.id, completed_order.id,
        GinningProductionCostCreate(cost_type=GinningCostType.ELECTRICITY, amount=Decimal("10000000")),
        ctx.actor_id,
    )

    summary = await costing_svc.get_cost_summary(
        ginning_company.id, completed_order.id, CostAllocationRequest(method=CostAllocationMethod.QUANTITY)
    )
    assert summary.raw_material_cost == Decimal("500000000")
    assert summary.other_costs_total == Decimal("10000000")
    assert summary.total_cost == Decimal("510000000")

    total_output = Decimal("32450") + Decimal("54800") + Decimal("4120") + Decimal("2900") + Decimal("1850")
    fiber_alloc = next(a for a in summary.allocations if a.product_type == GinningProductType.FIBER)
    expected_fiber_cost = summary.total_cost * (Decimal("32450") / total_output)
    assert abs(fiber_alloc.allocated_cost - expected_fiber_cost) < Decimal("0.01")

    # Allocations must sum back to total_cost
    total_allocated = sum((a.allocated_cost for a in summary.allocations), Decimal("0"))
    assert abs(total_allocated - summary.total_cost) < Decimal("0.01")


async def test_manual_percentage_allocation_must_sum_to_100(
    session: AsyncSession, ginning_company: Company, completed_order,
):
    costing_svc = GinningCostingService(session)
    outputs = completed_order.outputs
    bad_pct = {o.id: Decimal("10") for o in outputs}  # sums to 50, not 100

    with pytest.raises(BusinessRuleViolationError, match="sum to 100"):
        await costing_svc.get_cost_summary(
            ginning_company.id, completed_order.id,
            CostAllocationRequest(method=CostAllocationMethod.MANUAL_PERCENTAGE, manual_percentages=bad_pct),
        )


async def test_manual_percentage_allocation_correct(
    session: AsyncSession, ginning_company: Company, completed_order,
):
    costing_svc = GinningCostingService(session)
    outputs = sorted(completed_order.outputs, key=lambda o: o.product_type.value)
    pct = {outputs[0].id: Decimal("60"), **{o.id: Decimal("10") for o in outputs[1:]}}
    assert sum(pct.values()) == Decimal("100")

    summary = await costing_svc.get_cost_summary(
        ginning_company.id, completed_order.id,
        CostAllocationRequest(method=CostAllocationMethod.MANUAL_PERCENTAGE, manual_percentages=pct),
    )
    alloc_for_first = next(a for a in summary.allocations if a.output_id == outputs[0].id)
    assert abs(alloc_for_first.allocated_cost - summary.total_cost * Decimal("0.6")) < Decimal("0.01")


async def test_sales_value_allocation_requires_sales_history(
    session: AsyncSession, ginning_company: Company, completed_order,
):
    costing_svc = GinningCostingService(session)
    with pytest.raises(BusinessRuleViolationError, match="No sales-value reference"):
        await costing_svc.get_cost_summary(
            ginning_company.id, completed_order.id, CostAllocationRequest(method=CostAllocationMethod.SALES_VALUE)
        )


async def test_sales_value_allocation_with_sales_history(
    session: AsyncSession, ginning_company: Company, fiber_warehouse: Warehouse, customer: Counterparty, completed_order,
):
    ctx = _ctx(ginning_company.id)
    sale_svc = ExchangeSaleService(session)
    costing_svc = GinningCostingService(session)

    # Fiber sells for 25000/kg, Seed for 3000/kg -> fiber should get a much bigger cost share per kg
    await sale_svc.create(
        ginning_company.id,
        ExchangeSaleCreate(
            warehouse_id=fiber_warehouse.id, sale_date="2026-09-09", customer_id=customer.id,
            lines=[
                ExchangeSaleLineCreate(product_type=GinningProductType.FIBER, quantity_kg=Decimal("1000"), unit_price=Decimal("25000")),
                ExchangeSaleLineCreate(product_type=GinningProductType.SEED, quantity_kg=Decimal("1000"), unit_price=Decimal("3000")),
            ],
        ),
        ctx,
    )

    summary = await costing_svc.get_cost_summary(
        ginning_company.id, completed_order.id, CostAllocationRequest(method=CostAllocationMethod.SALES_VALUE)
    )
    fiber_alloc = next(a for a in summary.allocations if a.product_type == GinningProductType.FIBER)
    seed_alloc = next(a for a in summary.allocations if a.product_type == GinningProductType.SEED)
    # Fiber has less output kg (32450 vs 54800) but a much higher price -> higher cost/kg than seed
    assert fiber_alloc.cost_per_kg > seed_alloc.cost_per_kg
