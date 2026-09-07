"""
T3 — float -> Decimal precision regression test.

Posts 1000 ledger transactions of a 3-decimal quantity that is notorious for
floating-point drift (0.001 cannot be represented exactly in binary) and
asserts the resulting balance is *exactly* the expected Decimal, proving the
posting path no longer round-trips values through float().
"""
from datetime import date
from decimal import Decimal
import uuid

import pytest

from app.modules.stock.repository import StockRepository
from app.shared.enums import TransactionType


@pytest.mark.asyncio
async def test_1000_postings_of_0_001_kg_have_no_decimal_drift(
    session, test_company, test_warehouse
):
    repo = StockRepository(session)
    posted_by = uuid.uuid4()

    for _ in range(1000):
        await repo.post_transaction(
            company_id=test_company.id,
            warehouse_id=test_warehouse.id,
            transaction_type=TransactionType.OPENING_BALANCE,
            direction=1,
            quantity_kg=Decimal("0.001"),
            transaction_date=date(2026, 1, 1),
            posted_by=posted_by,
            reference_type="TEST",
            reference_id=uuid.uuid4(),
        )

    balance = await repo.get_balance(
        company_id=test_company.id,
        warehouse_id=test_warehouse.id,
    )
    assert balance == Decimal("1.000")
