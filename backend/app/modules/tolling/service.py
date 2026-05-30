from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid

from sqlalchemy import case as sa_case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.lot.models import Lot
from app.modules.counterparty.models import Counterparty
from app.modules.tolling.models import (
    TollingDailyRawIntake,
    TollingDistribution,
    TollingDistributionLine,
    TollingLot,
    TollingLotParticipant,
)
from app.modules.tolling.repository import (
    TollingDistributionRepository,
    TollingLotRepository,
    TollingParticipantRepository,
)
from app.modules.tolling.schemas import (
    DistributionCreate,
    DistributionLineOut,
    DistributionOut,
    DistributionUpdate,
    DailyRegisterOut,
    DailyRegisterRow,
    LotStockSummaryOut,
    LotSummaryOut,
    LotSummaryParticipantRow,
    ParticipantAdd,
    ParticipantOut,
    ParticipantUpdate,
    RawIntakeItemOut,
    TollingLotClose,
    TollingLotCreate,
    TollingLotOut,
)
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.models import Warehouse
from app.shared.base_service import AuditContext
from app.shared.enums import (
    AuditAction,
    LotStatus,
    TollingDistributionStatus,
    TollingLineType,
    TollingLotStatus,
    TransactionType,
    WarehouseType,
)
from app.shared.utils.lot_number import generate_lot_number


def _q3(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)


def _q5(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.00001"), rounding=ROUND_HALF_UP)


def _q2(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_lines(
    participants: list[TollingLotParticipant],
    daily_fg_kg: Decimal,
    cp_names: dict[uuid.UUID, str],
) -> list[dict]:
    total_raw = sum(Decimal(str(p.raw_kg_delivered)) for p in participants)
    if total_raw == Decimal("0"):
        raise BusinessRuleViolationError(
            "Lot ishtirokchilarida xom ashyo yetkazib berilgan (raw_kg_delivered) yo'q"
        )

    lines = []
    total_fee_kg = Decimal("0")

    for p in participants:
        share = Decimal(str(p.raw_kg_delivered)) / total_raw
        gross = _q3(daily_fg_kg * share)
        fee = _q3(gross * Decimal(str(p.fee_pct)) / Decimal("100"))
        net = gross - fee
        total_fee_kg += fee
        lines.append({
            "participant_id": p.id,
            "counterparty_id": p.counterparty_id,
            "line_type": TollingLineType.OWNER_NET,
            "gross_kg": float(gross),
            "fee_kg": float(fee),
            "net_kg": float(net),
            "ownership_share_pct": float(_q5(share * Decimal("100"))),
            "fee_pct_applied": float(p.fee_pct),
        })

    lines.append({
        "participant_id": None,
        "counterparty_id": None,
        "line_type": TollingLineType.PROCESSOR_FEE,
        "gross_kg": float(total_fee_kg),
        "fee_kg": 0.0,
        "net_kg": float(total_fee_kg),
        "ownership_share_pct": 0.0,
        "fee_pct_applied": 0.0,
    })

    return lines


def _build_line_out(line: TollingDistributionLine, cp_names: dict[uuid.UUID, str]) -> DistributionLineOut:
    cp_name = cp_names.get(line.counterparty_id) if line.counterparty_id else None
    return DistributionLineOut(
        id=line.id,
        participant_id=line.participant_id,
        counterparty_id=line.counterparty_id,
        counterparty_name=cp_name,
        line_type=line.line_type,
        gross_kg=Decimal(str(line.gross_kg)),
        fee_kg=Decimal(str(line.fee_kg)),
        net_kg=Decimal(str(line.net_kg)),
        ownership_share_pct=Decimal(str(line.ownership_share_pct)),
        fee_pct_applied=Decimal(str(line.fee_pct_applied)),
        fee_amount_uzs=Decimal(str(line.fee_amount_uzs)) if line.fee_amount_uzs is not None else None,
        fee_amount_usd=Decimal(str(line.fee_amount_usd)) if line.fee_amount_usd is not None else None,
        stock_transaction_id=line.stock_transaction_id,
    )


class TollingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.lot_repo = TollingLotRepository(session)
        self.part_repo = TollingParticipantRepository(session)
        self.dist_repo = TollingDistributionRepository(session)
        self.stock_repo = StockRepository(session)
        self.audit = AuditService(session)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _cp_names(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = await self.session.execute(
            select(Counterparty.id, Counterparty.name).where(Counterparty.id.in_(ids))
        )
        return {r.id: r.name for r in rows}

    async def _build_participant_out(
        self, p: TollingLotParticipant, cp_names: dict[uuid.UUID, str]
    ) -> ParticipantOut:
        return ParticipantOut(
            id=p.id,
            tolling_lot_id=p.tolling_lot_id,
            counterparty_id=p.counterparty_id,
            counterparty_name=cp_names.get(p.counterparty_id),
            contract_id=p.contract_id,
            raw_kg_delivered=Decimal(str(p.raw_kg_delivered)),
            fee_pct=Decimal(str(p.fee_pct)),
            fee_currency=p.fee_currency,
            fee_rate_per_kg=Decimal(str(p.fee_rate_per_kg)) if p.fee_rate_per_kg is not None else None,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )

    async def _build_lot_out(self, tl: TollingLot) -> TollingLotOut:
        cp_ids = [p.counterparty_id for p in tl.participants]
        cp_names = await self._cp_names(cp_ids)
        participants_out = [await self._build_participant_out(p, cp_names) for p in tl.participants]

        lot = await self.session.get(Lot, tl.lot_id)
        lot_number = lot.lot_number if lot else None

        total_raw = sum(Decimal(str(p.raw_kg_delivered)) for p in tl.participants)
        n_dist = await self.dist_repo.count_confirmed_for_lot(tl.id)
        total_fg = await self.dist_repo.sum_fg_for_lot(tl.id)

        return TollingLotOut(
            id=tl.id,
            company_id=tl.company_id,
            lot_id=tl.lot_id,
            lot_number=lot_number,
            status=tl.status,
            opened_at=tl.opened_at,
            closed_at=tl.closed_at,
            closed_by=tl.closed_by,
            close_reason=tl.close_reason,
            notes=tl.notes,
            created_by=tl.created_by,
            created_at=tl.created_at,
            updated_at=tl.updated_at,
            participants=participants_out,
            total_raw_kg=total_raw,
            total_distributions=n_dist,
            total_fg_distributed_kg=Decimal(str(total_fg)),
        )

    async def _build_dist_out(
        self, dist: TollingDistribution, cp_names: dict[uuid.UUID, str] | None = None
    ) -> DistributionOut:
        if cp_names is None:
            cp_ids = [ln.counterparty_id for ln in dist.lines if ln.counterparty_id]
            cp_ids += [
                ri.participant.counterparty_id
                for ri in dist.raw_intakes
                if ri.participant and ri.participant.counterparty_id
            ]
            cp_names = await self._cp_names(list(set(cp_ids)))

        lines_out = [_build_line_out(ln, cp_names) for ln in dist.lines]
        raw_intakes_out = [
            RawIntakeItemOut(
                id=ri.id,
                participant_id=ri.participant_id,
                counterparty_id=ri.participant.counterparty_id if ri.participant else None,
                counterparty_name=cp_names.get(ri.participant.counterparty_id) if ri.participant else None,
                raw_kg_received_today=Decimal(str(ri.raw_kg_received_today)),
            )
            for ri in dist.raw_intakes
        ]

        total_net = sum(
            Decimal(str(ln.net_kg)) for ln in dist.lines if ln.line_type == TollingLineType.OWNER_NET
        )
        total_fee = sum(
            Decimal(str(ln.net_kg)) for ln in dist.lines if ln.line_type == TollingLineType.PROCESSOR_FEE
        )

        return DistributionOut(
            id=dist.id,
            company_id=dist.company_id,
            tolling_lot_id=dist.tolling_lot_id,
            distribution_date=dist.distribution_date,
            daily_fg_kg_total=Decimal(str(dist.daily_fg_kg_total)),
            status=dist.status,
            confirmed_at=dist.confirmed_at,
            confirmed_by=dist.confirmed_by,
            notes=dist.notes,
            created_by=dist.created_by,
            created_at=dist.created_at,
            updated_at=dist.updated_at,
            lines=lines_out,
            raw_intakes=raw_intakes_out,
            total_net_kg=total_net,
            total_fee_kg=total_fee,
            total_kg_check=total_net + total_fee,
        )

    # ── Lot CRUD ─────────────────────────────────────────────────────────────

    async def create_lot(
        self, company_id: uuid.UUID, data: TollingLotCreate, ctx: AuditContext
    ) -> TollingLotOut:
        if await self.lot_repo.has_open_lot(company_id):
            raise BusinessRuleViolationError(
                "Hozirda ochiq tolling lot mavjud. Yangi lot ochish uchun avval uni yoping."
            )
        lot_number, year, seq = await generate_lot_number(self.session, company_id)
        lot = Lot(
            company_id=company_id,
            lot_number=lot_number,
            year=year,
            sequence_number=seq,
            status=LotStatus.OPEN,
            created_by=ctx.actor_id,
        )
        self.session.add(lot)
        await self.session.flush()
        await self.session.refresh(lot)

        tl = await self.lot_repo.create(
            company_id=company_id,
            lot_id=lot.id,
            status=TollingLotStatus.OPEN,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        tl.participants = []
        await self.audit.log(
            ctx=ctx,
            entity_type="tolling_lot",
            action=AuditAction.CREATE,
            entity_id=tl.id,
            entity_display=lot_number,
            after_data={"lot_number": lot_number},
        )
        return await self._build_lot_out(tl)

    async def get_active_lot(self, company_id: uuid.UUID) -> TollingLotOut | None:
        tl = await self.lot_repo.get_active(company_id)
        if tl is None:
            return None
        return await self._build_lot_out(tl)

    async def get_lot(self, lot_id: uuid.UUID) -> TollingLotOut:
        tl = await self.lot_repo.get_with_participants(lot_id)
        if tl is None:
            raise NotFoundError("TollingLot", lot_id)
        return await self._build_lot_out(tl)

    async def close_lot(
        self, lot_id: uuid.UUID, data: TollingLotClose, ctx: AuditContext
    ) -> TollingLotOut:
        tl = await self.lot_repo.get_with_participants(lot_id)
        if tl is None:
            raise NotFoundError("TollingLot", lot_id)
        if tl.status != TollingLotStatus.OPEN:
            raise BusinessRuleViolationError("Lot allaqachon yopilgan")

        tl.status = TollingLotStatus.CLOSED
        tl.closed_at = datetime.now(timezone.utc)
        tl.closed_by = ctx.actor_id
        tl.close_reason = data.close_reason
        await self.lot_repo.save(tl)

        lot = await self.session.get(Lot, tl.lot_id)
        if lot:
            lot.status = LotStatus.CLOSED
            lot.closed_at = datetime.now(timezone.utc)
            lot.closed_by = ctx.actor_id
            lot.close_reason = data.close_reason
            await self.session.flush()

        await self.audit.log(
            ctx=ctx, entity_type="tolling_lot", action=AuditAction.CLOSE,
            entity_id=tl.id, entity_display=str(lot.lot_number if lot else tl.id),
            after_data={"status": "CLOSED"},
        )
        return await self._build_lot_out(tl)

    # ── Participants ──────────────────────────────────────────────────────────

    async def add_participant(
        self, lot_id: uuid.UUID, data: ParticipantAdd, ctx: AuditContext
    ) -> ParticipantOut:
        tl = await self.lot_repo.get_with_participants(lot_id)
        if tl is None:
            raise NotFoundError("TollingLot", lot_id)
        if tl.status != TollingLotStatus.OPEN:
            raise BusinessRuleViolationError("Yopilgan lotga ishtirokchi qo'shib bo'lmaydi")

        existing_ids = {p.counterparty_id for p in tl.participants}
        if data.counterparty_id in existing_ids:
            raise BusinessRuleViolationError("Bu kontragent lotda allaqachon mavjud")

        p = await self.part_repo.create(
            tolling_lot_id=lot_id,
            counterparty_id=data.counterparty_id,
            contract_id=data.contract_id,
            raw_kg_delivered=float(data.raw_kg_delivered),
            fee_pct=float(data.fee_pct),
            fee_currency=data.fee_currency,
            fee_rate_per_kg=float(data.fee_rate_per_kg) if data.fee_rate_per_kg is not None else None,
            is_active=True,
        )
        cp_names = await self._cp_names([data.counterparty_id])
        return await self._build_participant_out(p, cp_names)

    async def update_participant(
        self, lot_id: uuid.UUID, participant_id: uuid.UUID, data: ParticipantUpdate, ctx: AuditContext
    ) -> ParticipantOut:
        p = await self.part_repo.get_by_id(participant_id)
        if p is None or p.tolling_lot_id != lot_id:
            raise NotFoundError("TollingLotParticipant", participant_id)

        if data.fee_pct is not None:
            p.fee_pct = float(data.fee_pct)
        if data.fee_rate_per_kg is not None:
            p.fee_rate_per_kg = float(data.fee_rate_per_kg)
        if data.raw_kg_delivered is not None:
            p.raw_kg_delivered = float(data.raw_kg_delivered)
        if data.is_active is not None:
            p.is_active = data.is_active

        await self.part_repo.save(p)
        cp_names = await self._cp_names([p.counterparty_id])
        return await self._build_participant_out(p, cp_names)

    async def remove_participant(self, lot_id: uuid.UUID, participant_id: uuid.UUID) -> None:
        p = await self.part_repo.get_by_id(participant_id)
        if p is None or p.tolling_lot_id != lot_id:
            raise NotFoundError("TollingLotParticipant", participant_id)
        if await self.part_repo.has_distributions(participant_id):
            raise BusinessRuleViolationError(
                "Bu ishtirokchida taqsimotlar mavjud, o'chirib bo'lmaydi"
            )
        await self.part_repo.delete(p)

    # ── Distributions ─────────────────────────────────────────────────────────

    async def create_distribution(
        self, company_id: uuid.UUID, data: DistributionCreate, ctx: AuditContext
    ) -> DistributionOut:
        tl = await self.lot_repo.get_with_participants(data.tolling_lot_id)
        if tl is None:
            raise NotFoundError("TollingLot", data.tolling_lot_id)
        if tl.status != TollingLotStatus.OPEN:
            raise BusinessRuleViolationError("Yopilgan lot uchun taqsimot yaratib bo'lmaydi")

        existing = await self.dist_repo.get_by_lot_date(data.tolling_lot_id, data.distribution_date)
        if existing is not None:
            raise BusinessRuleViolationError(
                f"Bu sana uchun taqsimot allaqachon mavjud: {data.distribution_date}"
            )

        dist = await self.dist_repo.create(
            company_id=company_id,
            tolling_lot_id=data.tolling_lot_id,
            distribution_date=data.distribution_date,
            daily_fg_kg_total=float(data.daily_fg_kg_total),
            status=TollingDistributionStatus.DRAFT,
            notes=data.notes,
            created_by=ctx.actor_id,
        )

        if data.raw_intakes:
            await self.dist_repo.replace_raw_intakes(
                dist,
                [{"participant_id": ri.participant_id, "raw_kg_received_today": float(ri.raw_kg_received_today)}
                 for ri in data.raw_intakes],
            )

        dist = await self.dist_repo.get_full(dist.id)
        return await self._build_dist_out(dist)

    async def get_distribution(self, dist_id: uuid.UUID) -> DistributionOut:
        dist = await self.dist_repo.get_full(dist_id)
        if dist is None:
            raise NotFoundError("TollingDistribution", dist_id)
        return await self._build_dist_out(dist)

    async def list_distributions(
        self,
        company_id: uuid.UUID,
        tolling_lot_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: TollingDistributionStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        from app.shared.schemas import PaginatedResponse
        items, total = await self.dist_repo.list_for_lot(
            company_id, tolling_lot_id, date_from, date_to, status, page, page_size
        )
        outs = [await self._build_dist_out(d) for d in items]
        return PaginatedResponse.build(outs, total, page, page_size)

    async def update_distribution(
        self, dist_id: uuid.UUID, data: DistributionUpdate, ctx: AuditContext
    ) -> DistributionOut:
        dist = await self.dist_repo.get_full(dist_id)
        if dist is None:
            raise NotFoundError("TollingDistribution", dist_id)
        if dist.status != TollingDistributionStatus.DRAFT:
            raise BusinessRuleViolationError("Faqat DRAFT holatidagi taqsimotni tahrirlash mumkin")

        if data.daily_fg_kg_total is not None:
            dist.daily_fg_kg_total = float(data.daily_fg_kg_total)
        if data.notes is not None:
            dist.notes = data.notes
        if data.raw_intakes is not None:
            await self.dist_repo.replace_raw_intakes(
                dist,
                [{"participant_id": ri.participant_id, "raw_kg_received_today": float(ri.raw_kg_received_today)}
                 for ri in data.raw_intakes],
            )

        await self.dist_repo.save(dist)
        dist = await self.dist_repo.get_full(dist.id)
        return await self._build_dist_out(dist)

    async def preview_distribution(self, dist_id: uuid.UUID) -> DistributionOut:
        dist = await self.dist_repo.get_full(dist_id)
        if dist is None:
            raise NotFoundError("TollingDistribution", dist_id)

        participants = await self.part_repo.get_active_for_lot(dist.tolling_lot_id)
        cp_ids = [p.counterparty_id for p in participants]
        cp_names = await self._cp_names(cp_ids)

        lines_data = _calculate_lines(participants, Decimal(str(dist.daily_fg_kg_total)), cp_names)

        preview_lines = []
        for ld in lines_data:
            preview_lines.append(DistributionLineOut(
                id=None,
                participant_id=ld["participant_id"],
                counterparty_id=ld["counterparty_id"],
                counterparty_name=cp_names.get(ld["counterparty_id"]) if ld["counterparty_id"] else None,
                line_type=ld["line_type"],
                gross_kg=Decimal(str(ld["gross_kg"])),
                fee_kg=Decimal(str(ld["fee_kg"])),
                net_kg=Decimal(str(ld["net_kg"])),
                ownership_share_pct=Decimal(str(ld["ownership_share_pct"])),
                fee_pct_applied=Decimal(str(ld["fee_pct_applied"])),
            ))

        ri_ids = [ri.participant.counterparty_id for ri in dist.raw_intakes if ri.participant]
        ri_names = await self._cp_names(ri_ids)
        raw_intakes_out = [
            RawIntakeItemOut(
                id=ri.id,
                participant_id=ri.participant_id,
                counterparty_id=ri.participant.counterparty_id if ri.participant else None,
                counterparty_name=ri_names.get(ri.participant.counterparty_id) if ri.participant else None,
                raw_kg_received_today=Decimal(str(ri.raw_kg_received_today)),
            )
            for ri in dist.raw_intakes
        ]

        total_net = sum(ln.net_kg for ln in preview_lines if ln.line_type == TollingLineType.OWNER_NET)
        total_fee = sum(ln.net_kg for ln in preview_lines if ln.line_type == TollingLineType.PROCESSOR_FEE)

        return DistributionOut(
            id=dist.id,
            company_id=dist.company_id,
            tolling_lot_id=dist.tolling_lot_id,
            distribution_date=dist.distribution_date,
            daily_fg_kg_total=Decimal(str(dist.daily_fg_kg_total)),
            status=dist.status,
            confirmed_at=dist.confirmed_at,
            confirmed_by=dist.confirmed_by,
            notes=dist.notes,
            created_by=dist.created_by,
            created_at=dist.created_at,
            updated_at=dist.updated_at,
            lines=preview_lines,
            raw_intakes=raw_intakes_out,
            total_net_kg=total_net,
            total_fee_kg=total_fee,
            total_kg_check=total_net + total_fee,
        )

    async def confirm_distribution(self, dist_id: uuid.UUID, ctx: AuditContext) -> DistributionOut:
        dist = await self.dist_repo.get_full(dist_id)
        if dist is None:
            raise NotFoundError("TollingDistribution", dist_id)
        if dist.status != TollingDistributionStatus.DRAFT:
            raise BusinessRuleViolationError("Taqsimot allaqachon tasdiqlangan")

        participants = await self.part_repo.get_active_for_lot(dist.tolling_lot_id)
        cp_ids = [p.counterparty_id for p in participants]
        cp_names = await self._cp_names(cp_ids)

        lines_data = _calculate_lines(participants, Decimal(str(dist.daily_fg_kg_total)), cp_names)
        await self.dist_repo.replace_lines(dist, lines_data)

        # Load warehouse IDs for this company
        fg_wh = await self._get_warehouse(dist.company_id, WarehouseType.FINISHED_GOODS)
        rc_wh = await self._get_warehouse(dist.company_id, WarehouseType.RAW_COTTON)

        tl = await self.lot_repo.get_by_id(dist.tolling_lot_id)

        # Post FG stock transactions per line
        dist = await self.dist_repo.get_full(dist.id)
        for line in dist.lines:
            if line.line_type == TollingLineType.OWNER_NET and fg_wh:
                tx = await self.stock_repo.post_transaction(
                    company_id=dist.company_id,
                    warehouse_id=fg_wh.id,
                    transaction_type=TransactionType.TOLLING_OWNER_INBOUND,
                    direction=1,
                    quantity_kg=Decimal(str(line.net_kg)),
                    transaction_date=dist.distribution_date,
                    posted_by=ctx.actor_id,
                    reference_type="TOLLING_DISTRIBUTION",
                    reference_id=dist.id,
                    lot_id=tl.lot_id if tl else None,
                    owner_id=line.counterparty_id,
                    owner_name=cp_names.get(line.counterparty_id) if line.counterparty_id else None,
                )
                line.stock_transaction_id = tx.id

            elif line.line_type == TollingLineType.PROCESSOR_FEE and fg_wh:
                tx = await self.stock_repo.post_transaction(
                    company_id=dist.company_id,
                    warehouse_id=fg_wh.id,
                    transaction_type=TransactionType.TOLLING_FEE_INBOUND,
                    direction=1,
                    quantity_kg=Decimal(str(line.net_kg)),
                    transaction_date=dist.distribution_date,
                    posted_by=ctx.actor_id,
                    reference_type="TOLLING_DISTRIBUTION",
                    reference_id=dist.id,
                    lot_id=tl.lot_id if tl else None,
                    owner_id=None,
                )
                line.stock_transaction_id = tx.id

        await self.session.flush()

        # Post raw cotton receipt transactions and update running totals
        for ri in dist.raw_intakes:
            if Decimal(str(ri.raw_kg_received_today)) > Decimal("0"):
                p = await self.part_repo.get_by_id(ri.participant_id)
                if p and rc_wh:
                    cp_name = cp_names.get(p.counterparty_id)
                    await self.stock_repo.post_transaction(
                        company_id=dist.company_id,
                        warehouse_id=rc_wh.id,
                        transaction_type=TransactionType.TOLLING_RAW_RECEIPT,
                        direction=1,
                        quantity_kg=Decimal(str(ri.raw_kg_received_today)),
                        transaction_date=dist.distribution_date,
                        posted_by=ctx.actor_id,
                        reference_type="TOLLING_DISTRIBUTION",
                        reference_id=dist.id,
                        owner_id=p.counterparty_id,
                        owner_name=cp_name,
                    )
                    p.raw_kg_delivered = float(
                        Decimal(str(p.raw_kg_delivered)) + Decimal(str(ri.raw_kg_received_today))
                    )
                    await self.session.flush()

        dist.status = TollingDistributionStatus.CONFIRMED
        dist.confirmed_at = datetime.now(timezone.utc)
        dist.confirmed_by = ctx.actor_id
        await self.dist_repo.save(dist)

        await self.audit.log(
            ctx=ctx, entity_type="tolling_distribution", action=AuditAction.SUBMIT,
            entity_id=dist.id, entity_display=str(dist.distribution_date),
            after_data={"status": "CONFIRMED"},
        )

        dist = await self.dist_repo.get_full(dist.id)
        return await self._build_dist_out(dist, cp_names)

    async def unconfirm_distribution(self, dist_id: uuid.UUID, ctx: AuditContext) -> DistributionOut:
        dist = await self.dist_repo.get_full(dist_id)
        if dist is None:
            raise NotFoundError("TollingDistribution", dist_id)
        if dist.status != TollingDistributionStatus.CONFIRMED:
            raise BusinessRuleViolationError("Taqsimot tasdiqlanmagan")

        from app.modules.stock.models import StockTransaction

        for line in dist.lines:
            if line.stock_transaction_id:
                tx = await self.session.get(StockTransaction, line.stock_transaction_id)
                if tx:
                    await self.stock_repo.post_transaction(
                        company_id=dist.company_id,
                        warehouse_id=tx.warehouse_id,
                        transaction_type=tx.transaction_type,
                        direction=tx.direction * -1,
                        quantity_kg=Decimal(str(tx.quantity_kg)),
                        transaction_date=dist.distribution_date,
                        posted_by=ctx.actor_id,
                        reference_type="TOLLING_DISTRIBUTION",
                        reference_id=dist.id,
                        lot_id=tx.lot_id,
                        owner_id=tx.owner_id,
                        owner_name=tx.owner_name,
                        notes=f"UNCONFIRM reversal of tx {tx.id}",
                    )
                line.stock_transaction_id = None

        # Reverse raw cotton receipts and reduce running totals
        for ri in dist.raw_intakes:
            if Decimal(str(ri.raw_kg_received_today)) > Decimal("0"):
                p = await self.part_repo.get_by_id(ri.participant_id)
                if p:
                    p.raw_kg_delivered = float(
                        max(Decimal("0"),
                            Decimal(str(p.raw_kg_delivered)) - Decimal(str(ri.raw_kg_received_today)))
                    )
                    await self.session.flush()

        await self.dist_repo.replace_lines(dist, [])
        dist.status = TollingDistributionStatus.DRAFT
        dist.confirmed_at = None
        dist.confirmed_by = None
        await self.dist_repo.save(dist)

        await self.audit.log(
            ctx=ctx, entity_type="tolling_distribution", action=AuditAction.REOPEN,
            entity_id=dist.id, entity_display=str(dist.distribution_date),
            after_data={"status": "DRAFT"},
        )
        dist = await self.dist_repo.get_full(dist.id)
        return await self._build_dist_out(dist)

    # ── Reports ───────────────────────────────────────────────────────────────

    async def lot_summary(self, company_id: uuid.UUID, lot_id: uuid.UUID) -> LotSummaryOut:
        tl = await self.lot_repo.get_with_participants(lot_id)
        if tl is None:
            raise NotFoundError("TollingLot", lot_id)

        from app.modules.stock.models import StockTransaction
        from sqlalchemy import func
        from app.modules.tolling.models import TollingDistributionLine as TDL

        cp_ids = [p.counterparty_id for p in tl.participants]
        cp_names = await self._cp_names(cp_ids)
        lot = await self.session.get(Lot, tl.lot_id)

        rows_result = await self.session.execute(
            select(
                TDL.counterparty_id,
                func.sum(TDL.gross_kg).label("total_gross"),
                func.sum(TDL.fee_kg).label("total_fee"),
                func.sum(TDL.net_kg).label("total_net"),
                func.sum(TDL.fee_amount_uzs).label("total_uzs"),
                func.sum(TDL.fee_amount_usd).label("total_usd"),
            )
            .join(TollingDistribution, TDL.distribution_id == TollingDistribution.id)
            .where(
                TollingDistribution.tolling_lot_id == lot_id,
                TollingDistribution.status == TollingDistributionStatus.CONFIRMED,
                TDL.line_type == TollingLineType.OWNER_NET,
            )
            .group_by(TDL.counterparty_id)
        )

        total_raw = sum(Decimal(str(p.raw_kg_delivered)) for p in tl.participants)
        participant_raw = {p.counterparty_id: Decimal(str(p.raw_kg_delivered)) for p in tl.participants}

        # Stock kirimi/chiqimi/qoldiq per owner from FG warehouse
        fg_wh = await self._get_warehouse(company_id, WarehouseType.FINISHED_GOODS)
        stock_by_owner: dict[uuid.UUID, tuple[Decimal, Decimal]] = {}
        if fg_wh and cp_ids:
            stock_result = await self.session.execute(
                select(
                    StockTransaction.owner_id,
                    func.coalesce(func.sum(
                        sa_case((StockTransaction.direction == 1, StockTransaction.quantity_kg), else_=0)
                    ), 0).label("kirimi"),
                    func.coalesce(func.sum(
                        sa_case((StockTransaction.direction == -1, StockTransaction.quantity_kg), else_=0)
                    ), 0).label("chiqimi"),
                )
                .where(
                    StockTransaction.company_id == company_id,
                    StockTransaction.warehouse_id == fg_wh.id,
                    StockTransaction.lot_id == tl.lot_id,
                    StockTransaction.owner_id.in_(cp_ids),
                )
                .group_by(StockTransaction.owner_id)
            )
            stock_by_owner = {
                r.owner_id: (Decimal(str(r.kirimi or 0)), Decimal(str(r.chiqimi or 0)))
                for r in stock_result
            }

        summary_rows = []
        for r in rows_result:
            share = (participant_raw.get(r.counterparty_id, Decimal("0")) / total_raw * 100) if total_raw else Decimal("0")
            kirimi, chiqimi = stock_by_owner.get(r.counterparty_id, (Decimal("0"), Decimal("0")))
            summary_rows.append(LotSummaryParticipantRow(
                counterparty_id=r.counterparty_id,
                counterparty_name=cp_names.get(r.counterparty_id, ""),
                raw_kg_delivered=participant_raw.get(r.counterparty_id, Decimal("0")),
                ownership_share_pct=_q5(share),
                total_gross_kg=Decimal(str(r.total_gross or 0)),
                total_fee_kg=Decimal(str(r.total_fee or 0)),
                total_net_kg=Decimal(str(r.total_net or 0)),
                fee_amount_uzs=Decimal(str(r.total_uzs)) if r.total_uzs else None,
                fee_amount_usd=Decimal(str(r.total_usd)) if r.total_usd else None,
                stock_kirimi_kg=kirimi,
                stock_chiqimi_kg=chiqimi,
                stock_qoldiq_kg=kirimi - chiqimi,
            ))

        totals_result = await self.session.execute(
            select(
                func.sum(TDL.gross_kg).label("total_gross"),
                func.sum(TDL.fee_kg).label("total_fee"),
                func.sum(TDL.net_kg).label("total_net"),
            )
            .join(TollingDistribution, TDL.distribution_id == TollingDistribution.id)
            .where(
                TollingDistribution.tolling_lot_id == lot_id,
                TollingDistribution.status == TollingDistributionStatus.CONFIRMED,
            )
        )
        totals = totals_result.one()

        return LotSummaryOut(
            tolling_lot_id=tl.id,
            lot_number=lot.lot_number if lot else str(tl.id),
            status=tl.status,
            opened_at=tl.opened_at,
            closed_at=tl.closed_at,
            rows=summary_rows,
            total_fg_kg=Decimal(str(totals.total_gross or 0)),
            total_fee_kg=Decimal(str(totals.total_fee or 0)),
            total_net_kg=Decimal(str(totals.total_net or 0)),
        )

    async def daily_register(
        self,
        company_id: uuid.UUID,
        tolling_lot_id: uuid.UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> DailyRegisterOut:
        items, _ = await self.dist_repo.list_for_lot(
            company_id, tolling_lot_id, date_from, date_to, page_size=1000
        )
        cp_ids: list[uuid.UUID] = []
        for d in items:
            cp_ids += [ln.counterparty_id for ln in d.lines if ln.counterparty_id]
        cp_names = await self._cp_names(list(set(cp_ids)))

        reg_rows = []
        for d in items:
            lines_out = [_build_line_out(ln, cp_names) for ln in d.lines]
            total_fee = sum(Decimal(str(ln.net_kg)) for ln in d.lines if ln.line_type == TollingLineType.PROCESSOR_FEE)
            total_net = sum(Decimal(str(ln.net_kg)) for ln in d.lines if ln.line_type == TollingLineType.OWNER_NET)
            reg_rows.append(DailyRegisterRow(
                distribution_id=d.id,
                distribution_date=d.distribution_date,
                daily_fg_kg_total=Decimal(str(d.daily_fg_kg_total)),
                status=d.status,
                lines=lines_out,
                total_fee_kg=total_fee,
                total_net_kg=total_net,
            ))

        return DailyRegisterOut(
            tolling_lot_id=tolling_lot_id,
            date_from=date_from,
            date_to=date_to,
            rows=reg_rows,
        )

    async def get_lot_stock_summary(self, company_id: uuid.UUID, lot_id: uuid.UUID) -> LotStockSummaryOut:
        from app.modules.stock.models import StockTransaction
        from sqlalchemy import func

        tl = await self.lot_repo.get_with_participants(lot_id)
        if tl is None:
            raise NotFoundError("TollingLot", lot_id)

        lot = await self.session.get(Lot, tl.lot_id)
        fg_wh = await self._get_warehouse(company_id, WarehouseType.FINISHED_GOODS)

        total_kirimi = Decimal("0")
        total_chiqimi = Decimal("0")

        if fg_wh:
            result = await self.session.execute(
                select(
                    func.coalesce(func.sum(
                        sa_case((StockTransaction.direction == 1, StockTransaction.quantity_kg), else_=0)
                    ), 0).label("kirimi"),
                    func.coalesce(func.sum(
                        sa_case((StockTransaction.direction == -1, StockTransaction.quantity_kg), else_=0)
                    ), 0).label("chiqimi"),
                )
                .where(
                    StockTransaction.company_id == company_id,
                    StockTransaction.warehouse_id == fg_wh.id,
                    StockTransaction.lot_id == tl.lot_id,
                    StockTransaction.owner_id.isnot(None),
                )
            )
            row = result.one()
            total_kirimi = Decimal(str(row.kirimi or 0))
            total_chiqimi = Decimal(str(row.chiqimi or 0))

        return LotStockSummaryOut(
            lot_id=tl.id,
            lot_number=lot.lot_number if lot else str(tl.id),
            total_kirimi_kg=total_kirimi,
            total_chiqimi_kg=total_chiqimi,
            total_qoldiq_kg=total_kirimi - total_chiqimi,
        )

    # ── Warehouse helpers ─────────────────────────────────────────────────────

    async def _get_warehouse(self, company_id: uuid.UUID, wh_type: WarehouseType) -> Warehouse | None:
        result = await self.session.execute(
            select(Warehouse).where(
                Warehouse.company_id == company_id,
                Warehouse.warehouse_type == wh_type,
                Warehouse.is_active == True,
            ).limit(1)
        )
        return result.scalar_one_or_none()

    # ── Excel export ──────────────────────────────────────────────────────────

    async def export_lot_summary_xlsx(self, company_id: uuid.UUID, lot_id: uuid.UUID) -> bytes:
        import io
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
        from openpyxl.utils import get_column_letter

        summary = await self.lot_summary(company_id, lot_id)

        company_result = await self.session.execute(
            select(__import__("app.modules.company.models", fromlist=["Company"]).Company)
            .where(__import__("app.modules.company.models", fromlist=["Company"]).Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        company_name = company.name if company else ""

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Tolling Lot Xulosasi"

        header_fill = PatternFill("solid", fgColor="1F4E79")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        totals_fill = PatternFill("solid", fgColor="D9D9D9")
        totals_font = Font(bold=True)
        num_fmt = '#,##0.000'
        cur_fmt = '#,##0.00'

        ws.merge_cells("A1:H1")
        ws["A1"] = company_name
        ws["A1"].font = Font(bold=True, size=14)
        ws["A1"].alignment = Alignment(horizontal="center")

        ws.merge_cells("A2:H2")
        period = f"Lot: {summary.lot_number}"
        if summary.opened_at:
            period += f"  ({summary.opened_at.strftime('%d.%m.%Y')})"
        if summary.closed_at:
            period += f" — {summary.closed_at.strftime('%d.%m.%Y')}"
        ws["A2"] = period
        ws["A2"].font = Font(italic=True, size=11)
        ws["A2"].alignment = Alignment(horizontal="center")

        headers = ["Kontragent", "Xom ashyo (kg)", "Ulush (%)", "FG brutto (kg)", "Hizmat haqi (kg)", "Hizmat haqi (UZS)", "Hizmat haqi (USD)", "FG netto (kg)"]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=4, column=ci, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", wrap_text=True)

        for ri, row in enumerate(summary.rows, 5):
            ws.cell(row=ri, column=1, value=row.counterparty_name)
            ws.cell(row=ri, column=2, value=float(row.raw_kg_delivered)).number_format = num_fmt
            ws.cell(row=ri, column=3, value=float(row.ownership_share_pct)).number_format = '0.00000'
            ws.cell(row=ri, column=4, value=float(row.total_gross_kg)).number_format = num_fmt
            ws.cell(row=ri, column=5, value=float(row.total_fee_kg)).number_format = num_fmt
            c_uzs = ws.cell(row=ri, column=6, value=float(row.fee_amount_uzs) if row.fee_amount_uzs else 0)
            c_uzs.number_format = cur_fmt
            c_usd = ws.cell(row=ri, column=7, value=float(row.fee_amount_usd) if row.fee_amount_usd else 0)
            c_usd.number_format = '0.0000'
            ws.cell(row=ri, column=8, value=float(row.total_net_kg)).number_format = num_fmt
            # Apply number format to kg columns
            for ci in [2, 4, 5, 8]:
                ws.cell(row=ri, column=ci).number_format = num_fmt

        total_row = 5 + len(summary.rows)
        ws.cell(row=total_row, column=1, value="JAMI").font = totals_font
        for col in range(1, 9):
            ws.cell(row=total_row, column=col).fill = totals_fill
            ws.cell(row=total_row, column=col).font = totals_font

        ws.cell(row=total_row, column=2, value=float(sum(r.raw_kg_delivered for r in summary.rows))).number_format = num_fmt
        ws.cell(row=total_row, column=4, value=float(summary.total_fg_kg)).number_format = num_fmt
        ws.cell(row=total_row, column=5, value=float(summary.total_fee_kg)).number_format = num_fmt
        ws.cell(row=total_row, column=8, value=float(summary.total_net_kg)).number_format = num_fmt

        ws.column_dimensions["A"].width = 30
        for ci in range(2, 9):
            ws.column_dimensions[get_column_letter(ci)].width = 18

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def export_daily_register_xlsx(
        self,
        company_id: uuid.UUID,
        tolling_lot_id: uuid.UUID | None,
        date_from: date | None,
        date_to: date | None,
    ) -> bytes:
        import io
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        register = await self.daily_register(company_id, tolling_lot_id, date_from, date_to)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Kunlik Reestr"

        header_fill = PatternFill("solid", fgColor="1F4E79")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        num_fmt = '#,##0.000'

        headers = ["Sana", "Tayyor mahsulot (kg)", "Holat", "Hizmat haqi (kg)", "Netto (kg)"]
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        for ri, row in enumerate(register.rows, 2):
            ws.cell(row=ri, column=1, value=str(row.distribution_date))
            ws.cell(row=ri, column=2, value=float(row.daily_fg_kg_total)).number_format = num_fmt
            ws.cell(row=ri, column=3, value=row.status.value)
            ws.cell(row=ri, column=4, value=float(row.total_fee_kg)).number_format = num_fmt
            ws.cell(row=ri, column=5, value=float(row.total_net_kg)).number_format = num_fmt
            for ci in [2, 4, 5]:
                ws.cell(row=ri, column=ci).number_format = num_fmt

        for ci in range(1, 6):
            ws.column_dimensions[get_column_letter(ci)].width = 20

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
