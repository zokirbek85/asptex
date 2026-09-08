from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.farmer_ledger.models import FarmerLedgerEntry
from app.shared.base_repository import BaseRepository
from app.shared.enums import FarmerLedgerEntryType


class FarmerLedgerRepository(BaseRepository[FarmerLedgerEntry]):
    model = FarmerLedgerEntry

    async def get_balance(self, company_id: uuid.UUID, farmer_id: uuid.UUID) -> Decimal:
        """Returns SUM(amount * direction) — positive = company owes farmer."""
        result = await self.session.execute(
            select(
                func.coalesce(func.sum(FarmerLedgerEntry.amount * FarmerLedgerEntry.direction), 0)
            ).where(
                FarmerLedgerEntry.company_id == company_id,
                FarmerLedgerEntry.farmer_id == farmer_id,
            )
        )
        val = result.scalar_one()
        return Decimal(str(val)) if val is not None else Decimal("0")

    async def get_balances_batch(
        self, company_id: uuid.UUID, farmer_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Decimal]:
        if not farmer_ids:
            return {}
        result = await self.session.execute(
            select(
                FarmerLedgerEntry.farmer_id,
                func.coalesce(func.sum(FarmerLedgerEntry.amount * FarmerLedgerEntry.direction), 0),
            )
            .where(
                FarmerLedgerEntry.company_id == company_id,
                FarmerLedgerEntry.farmer_id.in_(farmer_ids),
            )
            .group_by(FarmerLedgerEntry.farmer_id)
        )
        return {row[0]: Decimal(str(row[1])) for row in result}

    async def get_entries(
        self,
        company_id: uuid.UUID,
        farmer_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[FarmerLedgerEntry], int]:
        conditions = [FarmerLedgerEntry.company_id == company_id]
        if farmer_id is not None:
            conditions.append(FarmerLedgerEntry.farmer_id == farmer_id)
        if date_from is not None:
            conditions.append(FarmerLedgerEntry.entry_date >= date_from)
        if date_to is not None:
            conditions.append(FarmerLedgerEntry.entry_date <= date_to)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(FarmerLedgerEntry)
            .where(*conditions)
            .order_by(FarmerLedgerEntry.entry_date.desc(), FarmerLedgerEntry.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def post_entry(
        self,
        *,
        company_id: uuid.UUID,
        farmer_id: uuid.UUID,
        entry_type: FarmerLedgerEntryType,
        direction: int,
        amount: Decimal,
        entry_date: date,
        posted_by: uuid.UUID,
        reference_type: str | None = None,
        reference_id: uuid.UUID | None = None,
        currency: str = "UZS",
        farmer_name: str | None = None,
        notes: str | None = None,
    ) -> FarmerLedgerEntry:
        entry = FarmerLedgerEntry(
            company_id=company_id,
            farmer_id=farmer_id,
            entry_type=entry_type,
            direction=direction,
            amount=amount,
            currency=currency,
            reference_type=reference_type,
            reference_id=reference_id,
            entry_date=entry_date,
            posted_by=posted_by,
            farmer_name=farmer_name,
            notes=notes,
        )
        self.session.add(entry)
        await self.session.flush()
        await self.session.refresh(entry)
        return entry
