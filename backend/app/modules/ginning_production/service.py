from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.ginning_bunt.repository import GinningBuntRepository
from app.modules.ginning_production.models import (
    GinningProductionInput,
    GinningProductionOrder,
    GinningProductionOutput,
)
from app.modules.ginning_production.repository import GinningProductionOrderRepository
from app.modules.ginning_production.schemas import (
    GinningProductionCancel,
    GinningProductionOrderCreate,
    GinningProductionOrderResponse,
    GinningProductionOrderUpdate,
)
from app.modules.stock.concurrency import lock_balance_key
from app.modules.stock.repository import StockRepository
from app.modules.warehouse.repository import WarehouseRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, BuntStatus, GinningProductionStatus, TransactionType, WarehouseType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_ginning_production_number


class GinningProductionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = GinningProductionOrderRepository(session)
        self.bunt_repo = GinningBuntRepository(session)
        self.warehouse_repo = WarehouseRepository(session)
        self.stock_repo = StockRepository(session)
        self.audit = AuditService(session)

    async def build_response(self, order: GinningProductionOrder) -> GinningProductionOrderResponse:
        total_input = sum((i.quantity_kg for i in order.inputs), Decimal("0"))
        total_output = sum((o.quantity_kg for o in order.outputs), Decimal("0"))
        diff = total_input - total_output
        yield_pct = (total_output / total_input * 100) if total_input > 0 else Decimal("0")
        loss_pct = Decimal("100") - yield_pct if total_input > 0 else Decimal("0")

        input_responses = []
        for i in order.inputs:
            bunt = await self.bunt_repo.get_scoped_with_lot(i.bunt_id, order.company_id)
            input_responses.append({
                "id": i.id,
                "bunt_id": i.bunt_id,
                "bunt_lot_number": bunt.lot.lot_number if bunt else "",
                "quantity_kg": i.quantity_kg,
            })

        output_responses = []
        for o in order.outputs:
            warehouse = await self.warehouse_repo.get_by_id(o.warehouse_id)
            output_responses.append({
                "id": o.id,
                "product_type": o.product_type,
                "warehouse_id": o.warehouse_id,
                "warehouse_name": warehouse.name if warehouse else "",
                "quantity_kg": o.quantity_kg,
                "yield_pct": (o.quantity_kg / total_input * 100) if total_input > 0 else None,
                "notes": o.notes,
            })

        return GinningProductionOrderResponse(
            id=order.id,
            company_id=order.company_id,
            production_number=order.production_number,
            production_date=order.production_date,
            status=order.status,
            inputs=input_responses,
            outputs=output_responses,
            total_input_kg=total_input,
            total_output_kg=total_output,
            diff_kg=diff,
            yield_pct=yield_pct,
            loss_pct=loss_pct,
            completed_at=order.completed_at,
            cancelled_at=order.cancelled_at,
            cancel_reason=order.cancel_reason,
            notes=order.notes,
            created_at=order.created_at,
        )

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        status: GinningProductionStatus | None = None,
    ) -> PaginatedResponse[GinningProductionOrderResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, status)
        responses = [await self.build_response(o) for o in items]
        return PaginatedResponse.build(responses, total, page, page_size)

    async def get(self, order_id: uuid.UUID, company_id: uuid.UUID) -> GinningProductionOrder:
        order = await self.repo.get_scoped_with_lines(order_id, company_id)
        if order is None:
            raise NotFoundError("GinningProductionOrder", order_id)
        return order

    async def _validate_and_build_lines(
        self,
        company_id: uuid.UUID,
        inputs: list,
        outputs: list,
    ) -> None:
        for line in inputs:
            bunt = await self.bunt_repo.get_scoped_with_lot(line.bunt_id, company_id)
            if bunt is None:
                raise NotFoundError("GinningBunt", line.bunt_id)
            if bunt.status != BuntStatus.OPEN:
                raise BusinessRuleViolationError(f"Bunt {bunt.lot.lot_number} is not OPEN")
        for line in outputs:
            warehouse = await self.warehouse_repo.get_scoped_or_raise(line.warehouse_id, company_id, "Warehouse")
            if warehouse.warehouse_type != WarehouseType.FINISHED_GOODS:
                raise BusinessRuleViolationError(
                    f"Output warehouse {warehouse.name} must be a FINISHED_GOODS warehouse"
                )

    async def create(
        self, company_id: uuid.UUID, data: GinningProductionOrderCreate, ctx: AuditContext
    ) -> GinningProductionOrder:
        await self._validate_and_build_lines(company_id, data.inputs, data.outputs)

        production_number = await generate_ginning_production_number(self.session, company_id)
        order = GinningProductionOrder(
            company_id=company_id,
            production_number=production_number,
            production_date=data.production_date,
            status=GinningProductionStatus.DRAFT,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        order.inputs = [
            GinningProductionInput(bunt_id=i.bunt_id, quantity_kg=i.quantity_kg) for i in data.inputs
        ]
        order.outputs = [
            GinningProductionOutput(
                product_type=o.product_type, warehouse_id=o.warehouse_id,
                quantity_kg=o.quantity_kg, notes=o.notes,
            )
            for o in data.outputs
        ]
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order, attribute_names=["inputs", "outputs"])

        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_production_order",
            action=AuditAction.CREATE,
            entity_id=order.id,
            entity_display=order.production_number,
        )
        return order

    async def update(
        self, order_id: uuid.UUID, company_id: uuid.UUID, data: GinningProductionOrderUpdate, ctx: AuditContext
    ) -> GinningProductionOrder:
        order = await self.get(order_id, company_id)
        if order.status != GinningProductionStatus.DRAFT:
            raise BusinessRuleViolationError("Only a DRAFT production order can be edited")

        await self._validate_and_build_lines(company_id, data.inputs, data.outputs)

        order.inputs.clear()
        order.outputs.clear()
        await self.session.flush()
        order.inputs = [
            GinningProductionInput(bunt_id=i.bunt_id, quantity_kg=i.quantity_kg) for i in data.inputs
        ]
        order.outputs = [
            GinningProductionOutput(
                product_type=o.product_type, warehouse_id=o.warehouse_id,
                quantity_kg=o.quantity_kg, notes=o.notes,
            )
            for o in data.outputs
        ]
        if data.notes is not None:
            order.notes = data.notes
        self.session.add(order)
        await self.session.flush()
        await self.session.refresh(order, attribute_names=["inputs", "outputs"])
        return order

    async def complete(
        self, order_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext
    ) -> GinningProductionOrder:
        order = await self.get(order_id, company_id)
        if order.status != GinningProductionStatus.DRAFT:
            raise BusinessRuleViolationError("Only a DRAFT production order can be completed")

        for input_line in order.inputs:
            bunt = await self.bunt_repo.get_scoped_with_lot(input_line.bunt_id, company_id)
            if bunt is None:
                raise NotFoundError("GinningBunt", input_line.bunt_id)
            if bunt.status != BuntStatus.OPEN:
                raise BusinessRuleViolationError(f"Bunt {bunt.lot.lot_number} is not OPEN")

            await lock_balance_key(self.session, company_id, bunt.warehouse_id, bunt.lot_id, None, None)
            available = await self.stock_repo.get_balance(
                company_id=company_id, warehouse_id=bunt.warehouse_id, lot_id=bunt.lot_id, owner_id=None,
            )
            if available < input_line.quantity_kg:
                raise BusinessRuleViolationError(
                    f"Insufficient stock in bunt {bunt.lot.lot_number}: "
                    f"available {available} kg, requested {input_line.quantity_kg} kg"
                )

            tx = await self.stock_repo.post_transaction(
                company_id=company_id,
                warehouse_id=bunt.warehouse_id,
                transaction_type=TransactionType.PRODUCTION_ISSUE,
                direction=-1,
                quantity_kg=input_line.quantity_kg,
                transaction_date=order.production_date,
                posted_by=ctx.actor_id,
                reference_type="GINNING_PRODUCTION",
                reference_id=order.id,
                reference_line_id=input_line.id,
                lot_id=bunt.lot_id,
                owner_id=None,
                lot_number=bunt.lot.lot_number,
                notes=f"Ginning production {order.production_number}",
            )
            input_line.transaction_id = tx.id

        for output_line in order.outputs:
            await lock_balance_key(self.session, company_id, output_line.warehouse_id, None, None, None)
            tx = await self.stock_repo.post_transaction(
                company_id=company_id,
                warehouse_id=output_line.warehouse_id,
                transaction_type=TransactionType.PRODUCTION_INBOUND,
                direction=1,
                quantity_kg=output_line.quantity_kg,
                transaction_date=order.production_date,
                posted_by=ctx.actor_id,
                reference_type="GINNING_PRODUCTION",
                reference_id=order.id,
                reference_line_id=output_line.id,
                ginning_product_type=output_line.product_type,
                notes=f"Ginning production {order.production_number}",
            )
            output_line.transaction_id = tx.id

        order.total_input_kg = sum((i.quantity_kg for i in order.inputs), Decimal("0"))
        order.total_output_kg = sum((o.quantity_kg for o in order.outputs), Decimal("0"))
        order.status = GinningProductionStatus.COMPLETED
        order.completed_at = datetime.now(timezone.utc)
        order.completed_by = ctx.actor_id
        self.session.add(order)
        await self.session.flush()

        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_production_order",
            action=AuditAction.POST,
            entity_id=order.id,
            entity_display=order.production_number,
            after_data={
                "total_input_kg": str(order.total_input_kg),
                "total_output_kg": str(order.total_output_kg),
            },
        )
        return order

    async def cancel(
        self, order_id: uuid.UUID, company_id: uuid.UUID, data: GinningProductionCancel, ctx: AuditContext
    ) -> GinningProductionOrder:
        order = await self.get(order_id, company_id)
        if order.status == GinningProductionStatus.CANCELLED:
            raise BusinessRuleViolationError("Production order is already cancelled")

        if order.status == GinningProductionStatus.COMPLETED:
            await self._check_no_bale_references(order)
            for input_line in order.inputs:
                bunt = await self.bunt_repo.get_scoped_with_lot(input_line.bunt_id, company_id)
                await self.stock_repo.post_transaction(
                    company_id=company_id,
                    warehouse_id=bunt.warehouse_id,
                    transaction_type=TransactionType.PRODUCTION_ISSUE,
                    direction=1,
                    quantity_kg=input_line.quantity_kg,
                    transaction_date=order.production_date,
                    posted_by=ctx.actor_id,
                    reference_type="GINNING_PRODUCTION",
                    reference_id=order.id,
                    reference_line_id=input_line.id,
                    lot_id=bunt.lot_id,
                    owner_id=None,
                    lot_number=bunt.lot.lot_number,
                    notes=f"CANCEL reversal of {order.production_number}: {data.reason}",
                )
            for output_line in order.outputs:
                await self.stock_repo.post_transaction(
                    company_id=company_id,
                    warehouse_id=output_line.warehouse_id,
                    transaction_type=TransactionType.PRODUCTION_INBOUND,
                    direction=-1,
                    quantity_kg=output_line.quantity_kg,
                    transaction_date=order.production_date,
                    posted_by=ctx.actor_id,
                    reference_type="GINNING_PRODUCTION",
                    reference_id=order.id,
                    reference_line_id=output_line.id,
                    ginning_product_type=output_line.product_type,
                    notes=f"CANCEL reversal of {order.production_number}: {data.reason}",
                )

        order.status = GinningProductionStatus.CANCELLED
        order.cancelled_at = datetime.now(timezone.utc)
        order.cancelled_by = ctx.actor_id
        order.cancel_reason = data.reason
        self.session.add(order)
        await self.session.flush()

        await self.audit.log(
            ctx=ctx,
            entity_type="ginning_production_order",
            action=AuditAction.CANCEL,
            entity_id=order.id,
            entity_display=order.production_number,
            reason=data.reason,
        )
        return order

    async def _check_no_bale_references(self, order: GinningProductionOrder) -> None:
        """Guard extended in the Bale module: a completed order with bales already
        created from it must not be reversed without first removing those bales."""
        try:
            from app.modules.ginning_bale.repository import GinningBaleRepository
        except ImportError:
            return
        bale_repo = GinningBaleRepository(self.session)
        if await bale_repo.exists_for_order(order.id):
            raise BusinessRuleViolationError(
                "Cannot cancel: bales have already been created from this production order"
            )
