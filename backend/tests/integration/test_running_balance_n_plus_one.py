"""
T7 — N+1 regression test: get_warehouse_running_balance's SQL query count
must not scale with the number of tolling participants.
"""
from decimal import Decimal
import uuid

import pytest
from sqlalchemy import event

from app.modules.counterparty.models import Counterparty
from app.modules.daily_report.service import DailyReportService
from app.modules.lot.models import Lot
from app.modules.tolling.models import TollingLot, TollingLotParticipant
from app.shared.enums import CounterpartyType, LotStatus, TollingLotStatus
from tests.conftest import test_engine


async def _count_queries(coro):
    count = 0

    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        nonlocal count
        count += 1

    event.listen(test_engine.sync_engine, "before_cursor_execute", _before_cursor_execute)
    try:
        await coro
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", _before_cursor_execute)
    return count


@pytest.mark.asyncio
async def test_running_balance_query_count_independent_of_participant_count(
    session, test_company, test_warehouse
):
    lot = Lot(
        company_id=test_company.id, lot_number="2026-200", year=2026,
        sequence_number=200, status=LotStatus.OPEN,
    )
    session.add(lot)
    await session.flush()
    tl = TollingLot(company_id=test_company.id, lot_id=lot.id, status=TollingLotStatus.OPEN)
    session.add(tl)
    await session.flush()

    async def add_participants(n: int) -> None:
        for _ in range(n):
            cp = Counterparty(
                company_id=test_company.id, name=f"CP-{uuid.uuid4()}",
                counterparty_type=CounterpartyType.TOLLING_OWNER,
            )
            session.add(cp)
            await session.flush()
            session.add(TollingLotParticipant(
                tolling_lot_id=tl.id,
                counterparty_id=cp.id,
                raw_kg_delivered=Decimal("1000.000"),
                fee_pct=Decimal("10.00"),
            ))
        await session.flush()

    svc = DailyReportService(session)

    await add_participants(2)
    count_with_2 = await _count_queries(
        svc.get_warehouse_running_balance(test_company.id, test_warehouse.id)
    )

    await add_participants(8)  # 10 participants total now
    count_with_10 = await _count_queries(
        svc.get_warehouse_running_balance(test_company.id, test_warehouse.id)
    )

    # Query count must stay flat (batched), not grow with participant count.
    assert count_with_10 == count_with_2, (
        f"query count scaled with participants: {count_with_2} (2 participants) "
        f"vs {count_with_10} (10 participants) — expected equal (batched queries)"
    )
