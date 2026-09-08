"""
Phase 2 integration tests: Bunt multi-farmer traceability + Cotton Receiving posting.
Mirrors the acceptance scenario: 3 farmers deliver into one Bunt, quantities and
farmer ledger balances must reconcile exactly, and negative/invalid states are blocked.
"""
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError
from app.modules.company.models import Company
from app.modules.cotton_receiving.schemas import (
    CottonReceivingCancel,
    CottonReceivingCreate,
)
from app.modules.cotton_receiving.service import CottonReceivingService
from app.modules.counterparty.models import Counterparty
from app.modules.farmer_ledger.repository import FarmerLedgerRepository
from app.modules.ginning_bunt.schemas import GinningBuntClose, GinningBuntCreate
from app.modules.ginning_bunt.service import GinningBuntService
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import CompanyType, CounterpartyType, WarehouseType

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ginning_company(session: AsyncSession) -> Company:
    company = Company(name="Test Ginning Co", short_name="TGC", company_type=CompanyType.GINNING)
    session.add(company)
    await session.flush()
    return company


@pytest_asyncio.fixture
async def raw_cotton_warehouse(session: AsyncSession, ginning_company: Company) -> Warehouse:
    wh = Warehouse(
        company_id=ginning_company.id,
        code="WH-RAW-01",
        name="Raw Cotton",
        warehouse_type=WarehouseType.RAW_COTTON,
    )
    session.add(wh)
    await session.flush()
    return wh


@pytest_asyncio.fixture
async def farmers(session: AsyncSession, ginning_company: Company) -> list[Counterparty]:
    result = []
    for name in ("Farmer A", "Farmer B", "Farmer C"):
        f = Counterparty(company_id=ginning_company.id, name=name, counterparty_type=CounterpartyType.FARMER)
        session.add(f)
        result.append(f)
    await session.flush()
    return result


def _ctx(company_id: uuid.UUID) -> AuditContext:
    return AuditContext(
        actor_id=uuid.uuid4(),
        actor_username="tester",
        actor_full_name="Tester",
        company_id=company_id,
    )


async def test_bunt_multi_farmer_traceability_and_ledger(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    farmers: list[Counterparty],
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    farmer_a, farmer_b, farmer_c = farmers

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    assert bunt.status.value == "OPEN"

    deliveries = [
        (farmer_a, Decimal("10100"), Decimal("100"), Decimal("5000")),
        (farmer_b, Decimal("15150"), Decimal("150"), Decimal("5200")),
        (farmer_c, Decimal("20200"), Decimal("200"), Decimal("4800")),
    ]
    for farmer, gross, tare, price in deliveries:
        receiving = await receiving_svc.create(
            ginning_company.id,
            CottonReceivingCreate(
                bunt_id=bunt.id,
                farmer_id=farmer.id,
                receiving_date="2026-09-08",
                gross_weight_kg=gross,
                tare_weight_kg=tare,
                unit_price=price,
                grade="A",
            ),
            ctx,
        )
        assert receiving.net_weight_kg == gross - tare
        assert receiving.status.value == "DRAFT"

        posted = await receiving_svc.post(receiving.id, ginning_company.id, ctx)
        assert posted.status.value == "POSTED"

    # Bunt balance = sum of net weights = 45,000 kg
    balance = await bunt_svc.get_balance(bunt, ginning_company.id)
    assert balance == Decimal("45000")

    # Composition traces back to all 3 farmers with correct per-farmer totals
    composition = await bunt_svc.get_composition(bunt.id, ginning_company.id)
    comp_by_name = {c.farmer_name: c.total_net_kg for c in composition}
    assert comp_by_name == {
        "Farmer A": Decimal("10000"),
        "Farmer B": Decimal("15000"),
        "Farmer C": Decimal("20000"),
    }

    # Stock ledger balance matches directly too
    stock_repo = StockRepository(session)
    stock_balance = await stock_repo.get_balance(
        company_id=ginning_company.id, warehouse_id=raw_cotton_warehouse.id, lot_id=bunt.lot_id, owner_id=None,
    )
    assert stock_balance == Decimal("45000")

    # Farmer ledger balances = net_kg * price for each farmer
    ledger_repo = FarmerLedgerRepository(session)
    assert await ledger_repo.get_balance(ginning_company.id, farmer_a.id) == Decimal("10000") * Decimal("5000")
    assert await ledger_repo.get_balance(ginning_company.id, farmer_b.id) == Decimal("15000") * Decimal("5200")
    assert await ledger_repo.get_balance(ginning_company.id, farmer_c.id) == Decimal("20000") * Decimal("4800")


async def test_closed_bunt_rejects_new_receiving(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    farmers: list[Counterparty],
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    closed = await bunt_svc.close(bunt.id, ginning_company.id, GinningBuntClose(reason="test close"), ctx)
    assert closed.status.value == "CLOSED"

    with pytest.raises(BusinessRuleViolationError, match="CLOSED"):
        await receiving_svc.create(
            ginning_company.id,
            CottonReceivingCreate(
                bunt_id=bunt.id,
                farmer_id=farmers[0].id,
                receiving_date="2026-09-08",
                gross_weight_kg=Decimal("1000"),
                tare_weight_kg=Decimal("10"),
            ),
            ctx,
        )


async def test_post_requires_unit_price(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    farmers: list[Counterparty],
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(
            bunt_id=bunt.id,
            farmer_id=farmers[0].id,
            receiving_date="2026-09-08",
            gross_weight_kg=Decimal("1000"),
            tare_weight_kg=Decimal("10"),
        ),
        ctx,
    )
    assert receiving.unit_price is None

    with pytest.raises(BusinessRuleViolationError, match="unit_price"):
        await receiving_svc.post(receiving.id, ginning_company.id, ctx)


async def test_cancel_reverses_stock_and_ledger(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    farmers: list[Counterparty],
):
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(
            bunt_id=bunt.id,
            farmer_id=farmers[0].id,
            receiving_date="2026-09-08",
            gross_weight_kg=Decimal("1000"),
            tare_weight_kg=Decimal("10"),
            unit_price=Decimal("5000"),
        ),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)

    cancelled = await receiving_svc.cancel(
        receiving.id, ginning_company.id, CottonReceivingCancel(reason="wrong entry, testing reversal"), ctx
    )
    assert cancelled.status.value == "CANCELLED"

    balance = await bunt_svc.get_balance(bunt, ginning_company.id)
    assert balance == Decimal("0")

    ledger_repo = FarmerLedgerRepository(session)
    assert await ledger_repo.get_balance(ginning_company.id, farmers[0].id) == Decimal("0")


async def test_cancel_blocked_if_bunt_already_consumed(
    session: AsyncSession,
    ginning_company: Company,
    raw_cotton_warehouse: Warehouse,
    farmers: list[Counterparty],
):
    """Simulates partial consumption (e.g. by a future production order) via a direct
    stock posting, then verifies cancellation is blocked once the bunt balance can no
    longer cover the receiving being cancelled."""
    ctx = _ctx(ginning_company.id)
    bunt_svc = GinningBuntService(session)
    receiving_svc = CottonReceivingService(session)
    stock_repo = StockRepository(session)

    bunt = await bunt_svc.create(ginning_company.id, GinningBuntCreate(warehouse_id=raw_cotton_warehouse.id), ctx)
    receiving = await receiving_svc.create(
        ginning_company.id,
        CottonReceivingCreate(
            bunt_id=bunt.id,
            farmer_id=farmers[0].id,
            receiving_date="2026-09-08",
            gross_weight_kg=Decimal("1000"),
            tare_weight_kg=Decimal("0"),
            unit_price=Decimal("5000"),
        ),
        ctx,
    )
    await receiving_svc.post(receiving.id, ginning_company.id, ctx)

    from app.shared.enums import TransactionType

    await stock_repo.post_transaction(
        company_id=ginning_company.id,
        warehouse_id=raw_cotton_warehouse.id,
        transaction_type=TransactionType.PRODUCTION_ISSUE,
        direction=-1,
        quantity_kg=Decimal("600"),
        transaction_date=receiving.receiving_date,
        posted_by=ctx.actor_id,
        reference_type="TEST_CONSUMPTION",
        reference_id=uuid.uuid4(),
        lot_id=bunt.lot_id,
        owner_id=None,
    )

    with pytest.raises(BusinessRuleViolationError, match="already been partially consumed"):
        await receiving_svc.cancel(
            receiving.id, ginning_company.id, CottonReceivingCancel(reason="testing block"), ctx
        )
