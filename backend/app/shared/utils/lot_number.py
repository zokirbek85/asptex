"""
Lot number generation with SELECT FOR UPDATE to prevent race conditions.
Format: YYYY-NNN  (e.g. 2026-005)
"""

import uuid
from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


async def generate_lot_number(session: AsyncSession, company_id: uuid.UUID) -> tuple[str, int, int]:
    """
    Atomically generates the next lot number for the given company and current year.
    Returns (lot_number, year, sequence_number).
    Must be called inside an active transaction.
    """
    from app.modules.lot.models import LotNumberSequence  # lazy import to avoid circular

    year = date.today().year

    # Lock the row for this company+year
    result = await session.execute(
        select(LotNumberSequence)
        .where(
            LotNumberSequence.company_id == company_id,
            LotNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = LotNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        # Re-lock
        result = await session.execute(
            select(LotNumberSequence)
            .where(
                LotNumberSequence.company_id == company_id,
                LotNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    next_seq = seq.last_sequence
    lot_number = f"{year}-{next_seq:03d}"
    return lot_number, year, next_seq


async def generate_shipment_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next shipment number.
    Format: SH-YYYYMM-NNNN
    """
    from app.modules.shipment.models import ShipmentNumberSequence

    today = date.today()
    year_month = int(f"{today.year}{today.month:02d}")

    result = await session.execute(
        select(ShipmentNumberSequence)
        .where(
            ShipmentNumberSequence.company_id == company_id,
            ShipmentNumberSequence.year_month == year_month,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = ShipmentNumberSequence(company_id=company_id, year_month=year_month, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(ShipmentNumberSequence)
            .where(
                ShipmentNumberSequence.company_id == company_id,
                ShipmentNumberSequence.year_month == year_month,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"SH-{today.year}{today.month:02d}-{seq.last_sequence:04d}"


async def generate_adjustment_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next adjustment number.
    Format: ADJ-YYYY-NNNN
    """
    from app.modules.adjustment.models import AdjustmentNumberSequence

    year = date.today().year

    result = await session.execute(
        select(AdjustmentNumberSequence)
        .where(
            AdjustmentNumberSequence.company_id == company_id,
            AdjustmentNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = AdjustmentNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(AdjustmentNumberSequence)
            .where(
                AdjustmentNumberSequence.company_id == company_id,
                AdjustmentNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"ADJ-{year}-{seq.last_sequence:04d}"
