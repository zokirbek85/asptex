"""Phase 7 integration tests: Farmer settlements — payable, advance/payment, balance math."""
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
from app.modules.farmer_settlement.schemas import FarmerPaymentCancel, FarmerPaymentCreate
from app.modules.farmer_settlement.service import FarmerSettlementService
from app.modules.ginning_bunt.schemas import GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co 6", short_name="TGC6", company_type=CompanyType.GINNING)
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
async def farmer(session: AsyncSession, ginning_company: Company) -> Counterparty:
    f = Counterparty(company_id=ginning_company.id, name="Farmer Payable Test", counterparty_type=CounterpartyType.FARMER)
    session.add(f)
    await session.flush()
    return f


def _ctx(company_id: uuid.UUID) -> AuditContext:
    return AuditContext(actor_id=uuid.uuid4(), actor_username="tester", actor_full_name="Tester", company_id=company_id)


async def test_farmer_payable_advance_payment_balance(
    session: AsyncSession, ginning_company: Company, raw_cotton_warehouse: Warehouse, farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    settlement_svc = FarmerSettlementService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08", gross_weight_kg=Decimal("2000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000")),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)
    # Payable = 2000 * 5000 = 10,000,000

    balances = await settlement_svc.list_farmer_balances(ginning_company.id)
    farmer_balance = next(b for b in balances if b.farmer_id == farmer.id)
    assert farmer_balance.balance == Decimal("10000000")

    payment = await settlement_svc.create(
        ginning_company.id,
        FarmerPaymentCreate(farmer_id=farmer.id, payment_date="2026-09-09", amount=Decimal("4000000"), payment_method="BANK"),
        ctx,
    )
    assert payment.status.value == "DRAFT"

    posted = await settlement_svc.post(payment.id, ginning_company.id, ctx)
    assert posted.status.value == "POSTED"

    balances = await settlement_svc.list_farmer_balances(ginning_company.id)
    farmer_balance = next(b for b in balances if b.farmer_id == farmer.id)
    assert farmer_balance.balance == Decimal("10000000") - Decimal("4000000")  # 6,000,000 outstanding

    statement = await settlement_svc.get_farmer_statement(ginning_company.id, farmer.id)
    assert statement.total == 2  # RECEIVABLE_COTTON + PAYMENT


async def test_cancel_payment_restores_balance(
    session: AsyncSession, ginning_company: Company, raw_cotton_warehouse: Warehouse, farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    settlement_svc = FarmerSettlementService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(bunt_id=bunt.id, farmer_id=farmer.id, receiving_date="2026-09-08", gross_weight_kg=Decimal("1000"), tare_weight_kg=Decimal("0"), unit_price=Decimal("5000")),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)

    payment = await settlement_svc.create(
        ginning_company.id,
        FarmerPaymentCreate(farmer_id=farmer.id, payment_date="2026-09-09", amount=Decimal("1000000")),
        ctx,
    )
    await settlement_svc.post(payment.id, ginning_company.id, ctx)

    cancelled = await settlement_svc.cancel(
        payment.id, ginning_company.id, FarmerPaymentCancel(reason="wrong amount entered"), ctx
    )
    assert cancelled.status.value == "CANCELLED"

    balances = await settlement_svc.list_farmer_balances(ginning_company.id)
    farmer_balance = next(b for b in balances if b.farmer_id == farmer.id)
    assert farmer_balance.balance == Decimal("5000000")  # fully restored to original payable


async def test_cannot_post_already_posted_payment(
    session: AsyncSession, ginning_company: Company, farmer: Counterparty,
):
    ctx = _ctx(ginning_company.id)
    settlement_svc = FarmerSettlementService(session)

    payment = await settlement_svc.create(
        ginning_company.id,
        FarmerPaymentCreate(farmer_id=farmer.id, payment_date="2026-09-09", amount=Decimal("100000")),
        ctx,
    )
    await settlement_svc.post(payment.id, ginning_company.id, ctx)

    with pytest.raises(BusinessRuleViolationError, match="DRAFT"):
        await settlement_svc.post(payment.id, ginning_company.id, ctx)
