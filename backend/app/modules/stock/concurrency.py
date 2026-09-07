import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_balance_key(
    session: AsyncSession,
    company_id: uuid.UUID,
    warehouse_id: uuid.UUID,
    lot_id: uuid.UUID | None,
    count_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
) -> None:
    """Serializes concurrent postings against the same stock balance.

    Takes a transaction-scoped Postgres advisory lock keyed by the full
    identity tuple, so two concurrent requests touching the same balance
    cannot both read a stale current balance before either posts. The lock
    is released automatically when the enclosing transaction commits or
    rolls back.
    """
    key = f"{company_id}:{warehouse_id}:{lot_id}:{count_id}:{owner_id}"
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})
