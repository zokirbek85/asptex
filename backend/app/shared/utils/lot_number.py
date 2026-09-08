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


async def generate_cotton_receiving_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next cotton receiving number.
    Format: GIN-REC-YYYY-NNNN
    """
    from app.modules.cotton_receiving.models import CottonReceivingNumberSequence

    year = date.today().year

    result = await session.execute(
        select(CottonReceivingNumberSequence)
        .where(
            CottonReceivingNumberSequence.company_id == company_id,
            CottonReceivingNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = CottonReceivingNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(CottonReceivingNumberSequence)
            .where(
                CottonReceivingNumberSequence.company_id == company_id,
                CottonReceivingNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"GIN-REC-{year}-{seq.last_sequence:04d}"


async def generate_ginning_production_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next ginning production order number.
    Format: GIN-PROD-YYYY-NNNN
    """
    from app.modules.ginning_production.models import GinningProductionNumberSequence

    year = date.today().year

    result = await session.execute(
        select(GinningProductionNumberSequence)
        .where(
            GinningProductionNumberSequence.company_id == company_id,
            GinningProductionNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = GinningProductionNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(GinningProductionNumberSequence)
            .where(
                GinningProductionNumberSequence.company_id == company_id,
                GinningProductionNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"GIN-PROD-{year}-{seq.last_sequence:04d}"


async def generate_ginning_bale_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next ginning bale number.
    Format: GIN-BAL-YYYY-NNNNNN
    """
    from app.modules.ginning_bale.models import GinningBaleNumberSequence

    year = date.today().year

    result = await session.execute(
        select(GinningBaleNumberSequence)
        .where(
            GinningBaleNumberSequence.company_id == company_id,
            GinningBaleNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = GinningBaleNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(GinningBaleNumberSequence)
            .where(
                GinningBaleNumberSequence.company_id == company_id,
                GinningBaleNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"GIN-BAL-{year}-{seq.last_sequence:06d}"


async def generate_intercompany_transfer_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next intercompany transfer number (numbered on the source company).
    Format: GIN-TRF-YYYY-NNNN
    """
    from app.modules.intercompany_transfer.models import IntercompanyTransferNumberSequence

    year = date.today().year

    result = await session.execute(
        select(IntercompanyTransferNumberSequence)
        .where(
            IntercompanyTransferNumberSequence.company_id == company_id,
            IntercompanyTransferNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = IntercompanyTransferNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(IntercompanyTransferNumberSequence)
            .where(
                IntercompanyTransferNumberSequence.company_id == company_id,
                IntercompanyTransferNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"GIN-TRF-{year}-{seq.last_sequence:04d}"


async def generate_exchange_sale_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next exchange sale number.
    Format: GIN-SALE-YYYY-NNNN
    """
    from app.modules.exchange_sale.models import ExchangeSaleNumberSequence

    year = date.today().year

    result = await session.execute(
        select(ExchangeSaleNumberSequence)
        .where(
            ExchangeSaleNumberSequence.company_id == company_id,
            ExchangeSaleNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = ExchangeSaleNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(ExchangeSaleNumberSequence)
            .where(
                ExchangeSaleNumberSequence.company_id == company_id,
                ExchangeSaleNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"GIN-SALE-{year}-{seq.last_sequence:04d}"


async def generate_farmer_payment_number(session: AsyncSession, company_id: uuid.UUID) -> str:
    """
    Atomically generates the next farmer payment number.
    Format: GIN-PAY-YYYY-NNNN
    """
    from app.modules.farmer_settlement.models import FarmerPaymentNumberSequence

    year = date.today().year

    result = await session.execute(
        select(FarmerPaymentNumberSequence)
        .where(
            FarmerPaymentNumberSequence.company_id == company_id,
            FarmerPaymentNumberSequence.year == year,
        )
        .with_for_update()
    )
    seq = result.scalar_one_or_none()

    if seq is None:
        seq = FarmerPaymentNumberSequence(company_id=company_id, year=year, last_sequence=0)
        session.add(seq)
        await session.flush()
        result = await session.execute(
            select(FarmerPaymentNumberSequence)
            .where(
                FarmerPaymentNumberSequence.company_id == company_id,
                FarmerPaymentNumberSequence.year == year,
            )
            .with_for_update()
        )
        seq = result.scalar_one()

    seq.last_sequence += 1
    return f"GIN-PAY-{year}-{seq.last_sequence:04d}"
