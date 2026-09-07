from __future__ import annotations

from datetime import date
from decimal import Decimal
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.counterparty.models import Counterparty
from app.modules.count_catalog.models import CountCatalog
from app.modules.lot.models import Lot
from app.modules.shipment.models import (
    Shipment,
    ShipmentCancellation,
    ShipmentLine,
)
from app.modules.shipment.repository import ShipmentRepository
from app.modules.shipment.schemas import (
    ShipmentCreate,
    ShipmentLineCancelRequest,
    ShipmentLineResponse,
    ShipmentResponse,
)
from app.modules.stock.concurrency import lock_balance_key
from app.modules.stock.period_lock import assert_open_period
from app.modules.stock.repository import StockRepository
from app.modules.stock.schemas import StockWarning
from app.modules.stock.service import StockService
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, ShipmentStatus, TransactionType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_shipment_number


class ShipmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ShipmentRepository(session)
        self.stock_repo = StockRepository(session)
        self.stock_svc = StockService(session)
        self.audit = AuditService(session)

    async def _fetch_lot(self, lot_id: uuid.UUID) -> Lot:
        result = await self.session.execute(select(Lot).where(Lot.id == lot_id))
        lot = result.scalar_one_or_none()
        if lot is None:
            raise NotFoundError("Lot", lot_id)
        return lot

    async def _fetch_count(self, count_id: uuid.UUID) -> CountCatalog:
        result = await self.session.execute(
            select(CountCatalog).where(CountCatalog.id == count_id)
        )
        count = result.scalar_one_or_none()
        if count is None:
            raise NotFoundError("CountCatalog", count_id)
        return count

    async def _fetch_counterparty(self, cp_id: uuid.UUID) -> Counterparty:
        result = await self.session.execute(
            select(Counterparty).where(Counterparty.id == cp_id)
        )
        cp = result.scalar_one_or_none()
        if cp is None:
            raise NotFoundError("Counterparty", cp_id)
        return cp

    def _build_line_response(
        self,
        line: ShipmentLine,
        lots_by_id: dict[uuid.UUID, Lot],
        counts_by_id: dict[uuid.UUID, CountCatalog],
        owners_by_id: dict[uuid.UUID, Counterparty],
    ) -> ShipmentLineResponse:
        lot = lots_by_id.get(line.lot_id)
        count = counts_by_id.get(line.count_id)
        owner = owners_by_id.get(line.owner_id)
        if lot is None:
            raise NotFoundError("Lot", line.lot_id)
        if count is None:
            raise NotFoundError("CountCatalog", line.count_id)
        if owner is None:
            raise NotFoundError("Counterparty", line.owner_id)
        qty_kg = line.quantity_kg
        cancelled_kg = line.cancelled_kg
        return ShipmentLineResponse(
            id=line.id,
            line_number=line.line_number,
            lot_id=line.lot_id,
            lot_number=lot.lot_number,
            count_id=line.count_id,
            count_value=count.count_value,
            owner_id=line.owner_id,
            owner_name=owner.name,
            quantity_kg=qty_kg,
            quantity_bags=line.quantity_bags,
            cancelled_kg=cancelled_kg,
            cancelled_bags=line.cancelled_bags,
            is_fully_cancelled=line.is_fully_cancelled,
            net_kg=qty_kg - cancelled_kg,
        )

    async def build_response(
        self, shipment: Shipment, warnings: list[StockWarning] | None = None
    ) -> ShipmentResponse:
        # Batch-fetch lots/counts/owners for every line in one query each,
        # instead of three separate SELECTs per line (N+1).
        lines = shipment.lines or []
        lot_ids = {l.lot_id for l in lines}
        count_ids = {l.count_id for l in lines}
        owner_ids = {l.owner_id for l in lines} | {shipment.buyer_id}

        lots_by_id: dict[uuid.UUID, Lot] = {}
        if lot_ids:
            result = await self.session.execute(select(Lot).where(Lot.id.in_(lot_ids)))
            lots_by_id = {row.id: row for row in result.scalars().all()}

        counts_by_id: dict[uuid.UUID, CountCatalog] = {}
        if count_ids:
            result = await self.session.execute(
                select(CountCatalog).where(CountCatalog.id.in_(count_ids))
            )
            counts_by_id = {row.id: row for row in result.scalars().all()}

        owners_by_id: dict[uuid.UUID, Counterparty] = {}
        if owner_ids:
            result = await self.session.execute(
                select(Counterparty).where(Counterparty.id.in_(owner_ids))
            )
            owners_by_id = {row.id: row for row in result.scalars().all()}

        buyer = owners_by_id.get(shipment.buyer_id)
        if buyer is None:
            raise NotFoundError("Counterparty", shipment.buyer_id)

        line_responses = [
            self._build_line_response(l, lots_by_id, counts_by_id, owners_by_id) for l in lines
        ]
        total_kg = sum((lr.quantity_kg for lr in line_responses), Decimal("0"))
        net_kg = sum((lr.net_kg for lr in line_responses), Decimal("0"))
        return ShipmentResponse(
            id=shipment.id,
            shipment_number=shipment.shipment_number,
            shipment_date=shipment.shipment_date,
            status=shipment.status,
            buyer_id=shipment.buyer_id,
            buyer_name=buyer.name,
            contract_id=shipment.contract_id,
            warehouse_id=shipment.warehouse_id,
            lines=line_responses,
            total_kg=total_kg,
            net_kg=net_kg,
            notes=shipment.notes,
            created_at=shipment.created_at,
            warnings=warnings or None,
        )

    async def create(
        self,
        company_id: uuid.UUID,
        data: ShipmentCreate,
        ctx: AuditContext,
    ) -> tuple[Shipment, list[StockWarning]]:
        shipment_number = await generate_shipment_number(self.session, company_id)

        shipment = Shipment(
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            shipment_number=shipment_number,
            shipment_date=data.shipment_date,
            status=ShipmentStatus.ACTIVE,
            buyer_id=data.buyer_id,
            contract_id=data.contract_id,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        self.session.add(shipment)
        await self.session.flush()

        warnings: list[StockWarning] = []
        for idx, line_data in enumerate(data.lines, start=1):
            lot = await self._fetch_lot(line_data.lot_id)
            count = await self._fetch_count(line_data.count_id)
            owner = await self._fetch_counterparty(line_data.owner_id)

            qty_kg = line_data.quantity_kg
            await lock_balance_key(
                self.session, company_id, data.warehouse_id,
                line_data.lot_id, line_data.count_id, line_data.owner_id,
            )
            current, would_go_neg = await self.stock_svc.check_balance_and_warn(
                company_id=company_id,
                warehouse_id=data.warehouse_id,
                delta_kg=-qty_kg,
                lot_id=line_data.lot_id,
                count_id=line_data.count_id,
                owner_id=line_data.owner_id,
                lot_number=lot.lot_number,
                owner_name=owner.name,
            )
            if would_go_neg:
                warnings.append(StockWarning(
                    warehouse_id=data.warehouse_id,
                    lot_number=lot.lot_number,
                    count_value=count.count_value,
                    owner_name=owner.name,
                    current_kg=current,
                    after_kg=current - qty_kg,
                ))

            tx = await self.stock_repo.post_transaction(
                company_id=company_id,
                warehouse_id=data.warehouse_id,
                transaction_type=TransactionType.SHIPMENT_OUTBOUND,
                direction=-1,
                quantity_kg=qty_kg,
                transaction_date=data.shipment_date,
                posted_by=ctx.actor_id,
                reference_type="SHIPMENT",
                reference_id=shipment.id,
                lot_id=line_data.lot_id,
                count_id=line_data.count_id,
                owner_id=line_data.owner_id,
                quantity_bags=line_data.quantity_bags,
                lot_number=lot.lot_number,
                count_value=count.count_value,
                owner_name=owner.name,
            )

            line = ShipmentLine(
                shipment_id=shipment.id,
                lot_id=line_data.lot_id,
                count_id=line_data.count_id,
                owner_id=line_data.owner_id,
                quantity_kg=qty_kg,
                quantity_bags=line_data.quantity_bags,
                cancelled_kg=Decimal("0"),
                cancelled_bags=0,
                is_fully_cancelled=False,
                transaction_id=tx.id,
                line_number=idx,
                notes=line_data.notes,
            )
            self.session.add(line)

        await self.session.flush()
        # A blind refresh() only reloads already-loaded attributes; `.lines`
        # was never accessed on this brand-new object, so it would stay
        # unloaded and a later access (response building) would attempt an
        # implicit lazy-load, which AsyncSession does not support. Re-fetch
        # with eager loading instead.
        shipment = await self.repo.get_with_lines(shipment.id, company_id)

        await self.audit.log(
            ctx=ctx,
            entity_type="shipment",
            action=AuditAction.CREATE,
            entity_id=shipment.id,
            entity_display=shipment_number,
            after_data={"shipment_number": shipment_number, "lines": len(data.lines)},
        )
        return shipment, warnings

    async def cancel_line(
        self,
        shipment_id: uuid.UUID,
        company_id: uuid.UUID,
        line_id: uuid.UUID,
        data: ShipmentLineCancelRequest,
        ctx: AuditContext,
    ) -> Shipment:
        shipment = await self.repo.get_with_lines(shipment_id, company_id)
        if shipment is None:
            raise NotFoundError("Shipment", shipment_id)
        if shipment.status == ShipmentStatus.CANCELLED:
            raise BusinessRuleViolationError("Shipment is fully cancelled")

        line = next((l for l in shipment.lines if l.id == line_id), None)
        if line is None:
            raise NotFoundError("ShipmentLine", line_id)
        if line.is_fully_cancelled:
            raise BusinessRuleViolationError("Line is already fully cancelled")

        remaining_kg = Decimal(str(line.quantity_kg)) - Decimal(str(line.cancelled_kg))
        if data.quantity_kg > remaining_kg:
            raise BusinessRuleViolationError(
                f"Cannot cancel {data.quantity_kg} kg — only {remaining_kg} kg remaining"
            )

        lot = await self._fetch_lot(line.lot_id)
        count = await self._fetch_count(line.count_id)
        owner = await self._fetch_counterparty(line.owner_id)

        await assert_open_period(
            self.session, shipment.company_id, shipment.warehouse_id, shipment.shipment_date
        )

        reversal_tx = await self.stock_repo.post_transaction(
            company_id=shipment.company_id,
            warehouse_id=shipment.warehouse_id,
            transaction_type=TransactionType.SHIPMENT_CANCEL_REVERSAL,
            direction=1,
            quantity_kg=data.quantity_kg,
            transaction_date=shipment.shipment_date,
            posted_by=ctx.actor_id,
            reference_type="SHIPMENT",
            reference_id=shipment.id,
            reference_line_id=line.id,
            lot_id=line.lot_id,
            count_id=line.count_id,
            owner_id=line.owner_id,
            quantity_bags=data.quantity_bags,
            lot_number=lot.lot_number,
            count_value=count.count_value,
            owner_name=owner.name,
            notes=data.reason,
        )

        line.cancelled_kg = line.cancelled_kg + data.quantity_kg
        if data.quantity_bags is not None:
            line.cancelled_bags = line.cancelled_bags + data.quantity_bags
        new_remaining = line.quantity_kg - line.cancelled_kg
        line.is_fully_cancelled = new_remaining <= Decimal("0")

        cancellation = ShipmentCancellation(
            shipment_id=shipment.id,
            shipment_line_id=line.id,
            quantity_kg=data.quantity_kg,
            quantity_bags=data.quantity_bags,
            reason=data.reason,
            reversal_transaction_id=reversal_tx.id,
            cancelled_by=ctx.actor_id,
        )
        await self.repo.save_cancellation(cancellation)

        all_fully_cancelled = all(l.is_fully_cancelled for l in shipment.lines)
        any_cancelled = any(
            Decimal(str(l.cancelled_kg)) > Decimal("0") for l in shipment.lines
        )
        if all_fully_cancelled:
            shipment.status = ShipmentStatus.CANCELLED
        elif any_cancelled:
            shipment.status = ShipmentStatus.PARTIALLY_CANCELLED

        await self.repo.save(shipment)
        # save() expires (rather than reloads) relationship collections —
        # re-fetch eagerly so `.lines` is safe for the response builder.
        shipment = await self.repo.get_with_lines(shipment.id, company_id)

        await self.audit.log(
            ctx=ctx,
            entity_type="shipment",
            action=AuditAction.CANCEL,
            entity_id=shipment.id,
            entity_display=shipment.shipment_number,
            after_data={
                "line_id": str(line_id),
                "cancelled_kg": str(data.quantity_kg),
                "reason": data.reason,
            },
        )
        return shipment

    async def get(self, shipment_id: uuid.UUID, company_id: uuid.UUID) -> Shipment:
        shipment = await self.repo.get_with_lines(shipment_id, company_id)
        if shipment is None:
            raise NotFoundError("Shipment", shipment_id)
        return shipment

    async def list(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        buyer_id: uuid.UUID | None = None,
        status: ShipmentStatus | None = None,
        lot_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[Shipment]:
        items, total = await self.repo.list_paginated(
            company_id, warehouse_id, buyer_id, status, lot_id, date_from, date_to, page, page_size
        )
        return PaginatedResponse.build(items, total, page, page_size)
