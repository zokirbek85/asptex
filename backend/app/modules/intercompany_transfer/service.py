from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.company.repository import CompanyRepository
from app.modules.ginning_bale.repository import GinningBaleRepository
from app.modules.intercompany_transfer.models import IntercompanyTransfer, IntercompanyTransferLine
from app.modules.intercompany_transfer.repository import IntercompanyTransferRepository
from app.modules.intercompany_transfer.schemas import (
    IntercompanyTransferCancel,
    IntercompanyTransferCreate,
    IntercompanyTransferResponse,
)
from app.modules.stock.concurrency import lock_balance_key
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.repository import WarehouseRepository
from app.shared.base_service import AuditContext
from app.shared.enums import (
    AuditAction,
    CompanyType,
    GinningBaleStatus,
    IntercompanyTransferStatus,
    TransactionType,
    WarehouseType,
)
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_intercompany_transfer_number


class IntercompanyTransferService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = IntercompanyTransferRepository(session)
        self.company_repo = CompanyRepository(session)
        self.warehouse_repo = WarehouseRepository(session)
        self.bale_repo = GinningBaleRepository(session)
        self.stock_repo = StockRepository(session)
        self.audit = AuditService(session)

    async def build_response(self, transfer: IntercompanyTransfer) -> IntercompanyTransferResponse:
        source_company = await self.company_repo.get_by_id(transfer.source_company_id)
        dest_company = await self.company_repo.get_by_id(transfer.destination_company_id)

        line_responses = []
        for line in transfer.lines:
            bale_number = None
            if line.bale_id is not None:
                bale = await self.bale_repo.get_by_id(line.bale_id)
                bale_number = bale.bale_number if bale else None
            line_responses.append({
                "id": line.id, "bale_id": line.bale_id, "bale_number": bale_number,
                "quantity_kg": line.quantity_kg,
            })

        total_qty = sum((l.quantity_kg for l in transfer.lines), Decimal("0"))

        return IntercompanyTransferResponse(
            id=transfer.id,
            source_company_id=transfer.source_company_id,
            source_company_name=source_company.name if source_company else "",
            destination_company_id=transfer.destination_company_id,
            destination_company_name=dest_company.name if dest_company else "",
            source_warehouse_id=transfer.source_warehouse_id,
            destination_warehouse_id=transfer.destination_warehouse_id,
            product_type=transfer.product_type,
            transfer_number=transfer.transfer_number,
            transfer_date=transfer.transfer_date,
            status=transfer.status,
            unit_price=transfer.unit_price,
            currency=transfer.currency,
            total_value=transfer.total_value,
            total_quantity_kg=total_qty,
            lines=line_responses,
            confirmed_at=transfer.confirmed_at,
            cancelled_at=transfer.cancelled_at,
            cancel_reason=transfer.cancel_reason,
            notes=transfer.notes,
            created_at=transfer.created_at,
        )

    async def list(
        self, company_id: uuid.UUID, page: int, page_size: int, status: IntercompanyTransferStatus | None = None,
    ) -> PaginatedResponse[IntercompanyTransferResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, status)
        responses = [await self.build_response(t) for t in items]
        return PaginatedResponse.build(responses, total, page, page_size)

    async def get(self, transfer_id: uuid.UUID, company_id: uuid.UUID) -> IntercompanyTransfer:
        return await self.repo.get_visible_or_raise(transfer_id, company_id)

    async def create(
        self, source_company_id: uuid.UUID, data: IntercompanyTransferCreate, ctx: AuditContext
    ) -> IntercompanyTransfer:
        source_company = await self.company_repo.get_by_id_or_raise(source_company_id, "Company")
        if source_company.company_type != CompanyType.GINNING:
            raise BusinessRuleViolationError("Only a GINNING company can initiate an intercompany transfer")
        if data.destination_company_id == source_company_id:
            raise BusinessRuleViolationError("Source and destination company must differ")

        dest_company = await self.company_repo.get_by_id_or_raise(data.destination_company_id, "Company")
        if dest_company.company_type != CompanyType.YARN_SPINNING:
            raise BusinessRuleViolationError("Destination company must be a YARN_SPINNING company")
        if not dest_company.is_active:
            raise BusinessRuleViolationError("Destination company is not active")

        source_wh = await self.warehouse_repo.get_scoped_or_raise(
            data.source_warehouse_id, source_company_id, "Warehouse"
        )
        if source_wh.warehouse_type != WarehouseType.FINISHED_GOODS:
            raise BusinessRuleViolationError("Source warehouse must be a FINISHED_GOODS warehouse")

        dest_wh = await self.warehouse_repo.get_scoped_or_raise(
            data.destination_warehouse_id, data.destination_company_id, "Warehouse"
        )
        if dest_wh.warehouse_type != WarehouseType.RAW_COTTON:
            raise BusinessRuleViolationError("Destination warehouse must be a RAW_COTTON warehouse")

        for line in data.lines:
            if line.bale_id is not None:
                bale = await self.bale_repo.get_scoped_or_raise(line.bale_id, source_company_id, "GinningBale")
                if bale.status != GinningBaleStatus.IN_STOCK:
                    raise BusinessRuleViolationError(f"Bale {bale.bale_number} is not IN_STOCK")

        transfer_number = await generate_intercompany_transfer_number(self.session, source_company_id)
        total_qty = sum((l.quantity_kg for l in data.lines), Decimal("0"))
        total_value = (total_qty * data.unit_price) if data.unit_price is not None else None

        transfer = IntercompanyTransfer(
            source_company_id=source_company_id,
            destination_company_id=data.destination_company_id,
            source_warehouse_id=data.source_warehouse_id,
            destination_warehouse_id=data.destination_warehouse_id,
            product_type=data.product_type,
            transfer_number=transfer_number,
            transfer_date=data.transfer_date,
            status=IntercompanyTransferStatus.DRAFT,
            unit_price=data.unit_price,
            currency=data.currency,
            total_value=total_value,
            total_quantity_kg=total_qty,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        transfer.lines = [
            IntercompanyTransferLine(bale_id=l.bale_id, quantity_kg=l.quantity_kg) for l in data.lines
        ]
        self.session.add(transfer)
        await self.session.flush()
        await self.session.refresh(transfer, attribute_names=["lines"])

        await self.audit.log(
            ctx=ctx, entity_type="intercompany_transfer", action=AuditAction.CREATE,
            entity_id=transfer.id, entity_display=transfer.transfer_number,
        )
        return transfer

    async def confirm(
        self, transfer_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext
    ) -> IntercompanyTransfer:
        transfer = await self.repo.get_visible_or_raise(transfer_id, company_id)
        if transfer.source_company_id != company_id:
            raise BusinessRuleViolationError("Only the source company can confirm this transfer")
        if transfer.status != IntercompanyTransferStatus.DRAFT:
            raise BusinessRuleViolationError("Only a DRAFT transfer can be confirmed")

        await lock_balance_key(
            self.session, transfer.source_company_id, transfer.source_warehouse_id, None, None, None
        )
        available = await self.stock_repo.get_balance(
            company_id=transfer.source_company_id,
            warehouse_id=transfer.source_warehouse_id,
            ginning_product_type=transfer.product_type,
        )
        total_qty = sum((l.quantity_kg for l in transfer.lines), Decimal("0"))
        if available < total_qty:
            raise BusinessRuleViolationError(
                f"Insufficient stock: available {available} kg, requested {total_qty} kg"
            )

        for line in transfer.lines:
            source_tx = await self.stock_repo.post_transaction(
                company_id=transfer.source_company_id,
                warehouse_id=transfer.source_warehouse_id,
                transaction_type=TransactionType.SHIPMENT_OUTBOUND,
                direction=-1,
                quantity_kg=line.quantity_kg,
                transaction_date=transfer.transfer_date,
                posted_by=ctx.actor_id,
                reference_type="INTERCOMPANY_TRANSFER",
                reference_id=transfer.id,
                reference_line_id=line.id,
                ginning_product_type=transfer.product_type,
                notes=f"Intercompany transfer {transfer.transfer_number} to destination company",
            )
            dest_tx = await self.stock_repo.post_transaction(
                company_id=transfer.destination_company_id,
                warehouse_id=transfer.destination_warehouse_id,
                transaction_type=TransactionType.RECEIPT,
                direction=1,
                quantity_kg=line.quantity_kg,
                transaction_date=transfer.transfer_date,
                posted_by=ctx.actor_id,
                reference_type="INTERCOMPANY_TRANSFER",
                reference_id=transfer.id,
                reference_line_id=line.id,
                notes=f"Intercompany transfer {transfer.transfer_number} from source company",
            )
            line.source_transaction_id = source_tx.id
            line.destination_transaction_id = dest_tx.id

            if line.bale_id is not None:
                bale = await self.bale_repo.get_by_id(line.bale_id)
                bale.status = GinningBaleStatus.TRANSFERRED
                bale.sold_reference_type = "INTERCOMPANY_TRANSFER"
                bale.sold_reference_id = transfer.id

        transfer.status = IntercompanyTransferStatus.CONFIRMED
        transfer.confirmed_at = datetime.now(timezone.utc)
        transfer.confirmed_by = ctx.actor_id
        self.session.add(transfer)
        await self.session.flush()

        await self.audit.log(
            ctx=ctx, entity_type="intercompany_transfer", action=AuditAction.POST,
            entity_id=transfer.id, entity_display=transfer.transfer_number,
            after_data={"total_quantity_kg": str(total_qty)},
        )
        return transfer

    async def cancel(
        self, transfer_id: uuid.UUID, company_id: uuid.UUID, data: IntercompanyTransferCancel, ctx: AuditContext
    ) -> IntercompanyTransfer:
        transfer = await self.repo.get_visible_or_raise(transfer_id, company_id)
        if transfer.source_company_id != company_id:
            raise BusinessRuleViolationError("Only the source company can cancel this transfer")
        if transfer.status == IntercompanyTransferStatus.CANCELLED:
            raise BusinessRuleViolationError("Transfer is already cancelled")

        if transfer.status == IntercompanyTransferStatus.CONFIRMED:
            for line in transfer.lines:
                await self.stock_repo.post_transaction(
                    company_id=transfer.source_company_id,
                    warehouse_id=transfer.source_warehouse_id,
                    transaction_type=TransactionType.SHIPMENT_OUTBOUND,
                    direction=1,
                    quantity_kg=line.quantity_kg,
                    transaction_date=transfer.transfer_date,
                    posted_by=ctx.actor_id,
                    reference_type="INTERCOMPANY_TRANSFER",
                    reference_id=transfer.id,
                    reference_line_id=line.id,
                    ginning_product_type=transfer.product_type,
                    notes=f"CANCEL reversal of {transfer.transfer_number}: {data.reason}",
                )
                await self.stock_repo.post_transaction(
                    company_id=transfer.destination_company_id,
                    warehouse_id=transfer.destination_warehouse_id,
                    transaction_type=TransactionType.RECEIPT,
                    direction=-1,
                    quantity_kg=line.quantity_kg,
                    transaction_date=transfer.transfer_date,
                    posted_by=ctx.actor_id,
                    reference_type="INTERCOMPANY_TRANSFER",
                    reference_id=transfer.id,
                    reference_line_id=line.id,
                    notes=f"CANCEL reversal of {transfer.transfer_number}: {data.reason}",
                )
                if line.bale_id is not None:
                    bale = await self.bale_repo.get_by_id(line.bale_id)
                    bale.status = GinningBaleStatus.IN_STOCK
                    bale.sold_reference_type = None
                    bale.sold_reference_id = None

        transfer.status = IntercompanyTransferStatus.CANCELLED
        transfer.cancelled_at = datetime.now(timezone.utc)
        transfer.cancelled_by = ctx.actor_id
        transfer.cancel_reason = data.reason
        self.session.add(transfer)
        await self.session.flush()

        await self.audit.log(
            ctx=ctx, entity_type="intercompany_transfer", action=AuditAction.CANCEL,
            entity_id=transfer.id, entity_display=transfer.transfer_number, reason=data.reason,
        )
        return transfer
