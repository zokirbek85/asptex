from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.counterparty.repository import CounterpartyRepository
from app.modules.exchange_sale.models import ExchangeSale, ExchangeSaleCancellation, ExchangeSaleLine
from app.modules.exchange_sale.repository import ExchangeSaleRepository
from app.modules.exchange_sale.schemas import (
    ExchangeSaleCreate,
    ExchangeSaleLineCancelRequest,
    ExchangeSaleLineResponse,
    ExchangeSaleResponse,
)
from app.modules.ginning_bale.repository import GinningBaleRepository
from app.modules.stock.concurrency import lock_balance_key
from app.modules.stock.repository import StockRepository
from app.modules.stock.service import StockService
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, ExchangeSaleStatus, GinningBaleStatus, TransactionType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_exchange_sale_number


class ExchangeSaleService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ExchangeSaleRepository(session)
        self.counterparty_repo = CounterpartyRepository(session)
        self.bale_repo = GinningBaleRepository(session)
        self.stock_repo = StockRepository(session)
        self.stock_svc = StockService(session)
        self.audit = AuditService(session)

    async def _line_response(self, line: ExchangeSaleLine) -> ExchangeSaleLineResponse:
        bale_number = None
        if line.bale_id is not None:
            bale = await self.bale_repo.get_by_id(line.bale_id)
            bale_number = bale.bale_number if bale else None
        return ExchangeSaleLineResponse(
            id=line.id,
            line_number=line.line_number,
            product_type=line.product_type,
            bale_id=line.bale_id,
            bale_number=bale_number,
            quantity_kg=line.quantity_kg,
            unit_price=line.unit_price,
            currency=line.currency,
            total_amount=line.total_amount,
            cancelled_kg=line.cancelled_kg,
            is_fully_cancelled=line.is_fully_cancelled,
            net_kg=line.quantity_kg - line.cancelled_kg,
            notes=line.notes,
        )

    async def build_response(self, sale: ExchangeSale) -> ExchangeSaleResponse:
        customer = await self.counterparty_repo.get_by_id(sale.customer_id)
        line_responses = [await self._line_response(l) for l in sale.lines]
        total_kg = sum((l.quantity_kg for l in line_responses), Decimal("0"))
        net_kg = sum((l.net_kg for l in line_responses), Decimal("0"))
        total_value = sum((l.total_amount for l in line_responses), Decimal("0"))
        return ExchangeSaleResponse(
            id=sale.id,
            company_id=sale.company_id,
            warehouse_id=sale.warehouse_id,
            sale_number=sale.sale_number,
            sale_date=sale.sale_date,
            status=sale.status,
            customer_id=sale.customer_id,
            customer_name=customer.name if customer else "",
            contract_id=sale.contract_id,
            exchange_name=sale.exchange_name,
            exchange_lot_number=sale.exchange_lot_number,
            commission_amount=sale.commission_amount,
            broker_name=sale.broker_name,
            transport_cost=sale.transport_cost,
            other_costs=sale.other_costs,
            payment_status=sale.payment_status,
            lines=line_responses,
            total_kg=total_kg,
            net_kg=net_kg,
            total_value=total_value,
            notes=sale.notes,
            created_at=sale.created_at,
        )

    async def list(
        self, company_id: uuid.UUID, page: int, page_size: int,
        warehouse_id: uuid.UUID | None = None, customer_id: uuid.UUID | None = None,
        status: ExchangeSaleStatus | None = None,
    ) -> PaginatedResponse[ExchangeSaleResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, warehouse_id, customer_id, status)
        responses = [await self.build_response(s) for s in items]
        return PaginatedResponse.build(responses, total, page, page_size)

    async def get(self, sale_id: uuid.UUID, company_id: uuid.UUID) -> ExchangeSale:
        sale = await self.repo.get_with_lines(sale_id, company_id)
        if sale is None:
            raise NotFoundError("ExchangeSale", sale_id)
        return sale

    async def create(
        self, company_id: uuid.UUID, data: ExchangeSaleCreate, ctx: AuditContext
    ) -> ExchangeSale:
        customer = await self.counterparty_repo.get_scoped_or_raise(data.customer_id, company_id, "Counterparty")

        sale_number = await generate_exchange_sale_number(self.session, company_id)
        sale = ExchangeSale(
            company_id=company_id,
            warehouse_id=data.warehouse_id,
            sale_number=sale_number,
            sale_date=data.sale_date,
            status=ExchangeSaleStatus.ACTIVE,
            customer_id=data.customer_id,
            contract_id=data.contract_id,
            exchange_name=data.exchange_name,
            exchange_lot_number=data.exchange_lot_number,
            commission_amount=data.commission_amount,
            broker_name=data.broker_name,
            transport_cost=data.transport_cost,
            other_costs=data.other_costs,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        self.session.add(sale)
        await self.session.flush()

        for idx, line_data in enumerate(data.lines, start=1):
            if line_data.bale_id is not None:
                bale = await self.bale_repo.get_scoped_or_raise(line_data.bale_id, company_id, "GinningBale")
                if bale.status != GinningBaleStatus.IN_STOCK:
                    raise BusinessRuleViolationError(f"Bale {bale.bale_number} is not IN_STOCK")

            await lock_balance_key(self.session, company_id, data.warehouse_id, None, None, None)
            current, would_go_negative = await self.stock_svc.check_balance_and_warn(
                company_id=company_id,
                warehouse_id=data.warehouse_id,
                delta_kg=-line_data.quantity_kg,
                ginning_product_type=line_data.product_type,
            )
            if would_go_negative:
                raise BusinessRuleViolationError(
                    f"Insufficient {line_data.product_type.value} stock: "
                    f"available {current} kg, requested {line_data.quantity_kg} kg"
                )

            tx = await self.stock_repo.post_transaction(
                company_id=company_id,
                warehouse_id=data.warehouse_id,
                transaction_type=TransactionType.SHIPMENT_OUTBOUND,
                direction=-1,
                quantity_kg=line_data.quantity_kg,
                transaction_date=data.sale_date,
                posted_by=ctx.actor_id,
                reference_type="EXCHANGE_SALE",
                reference_id=sale.id,
                ginning_product_type=line_data.product_type,
                notes=f"Exchange sale {sale_number}",
            )

            line = ExchangeSaleLine(
                sale_id=sale.id,
                product_type=line_data.product_type,
                bale_id=line_data.bale_id,
                quantity_kg=line_data.quantity_kg,
                unit_price=line_data.unit_price,
                currency=line_data.currency,
                total_amount=line_data.quantity_kg * line_data.unit_price,
                transaction_id=tx.id,
                line_number=idx,
                notes=line_data.notes,
            )
            self.session.add(line)

            if line_data.bale_id is not None:
                bale = await self.bale_repo.get_by_id(line_data.bale_id)
                bale.status = GinningBaleStatus.SOLD
                bale.sold_reference_type = "EXCHANGE_SALE"
                bale.sold_reference_id = sale.id

        await self.session.flush()
        sale = await self.repo.get_with_lines(sale.id, company_id)

        await self.audit.log(
            ctx=ctx, entity_type="exchange_sale", action=AuditAction.CREATE,
            entity_id=sale.id, entity_display=sale_number,
            after_data={"lines": len(data.lines)},
        )
        return sale

    async def cancel_line(
        self, sale_id: uuid.UUID, company_id: uuid.UUID, line_id: uuid.UUID,
        data: ExchangeSaleLineCancelRequest, ctx: AuditContext,
    ) -> ExchangeSale:
        sale = await self.get(sale_id, company_id)
        if sale.status == ExchangeSaleStatus.CANCELLED:
            raise BusinessRuleViolationError("Sale is fully cancelled")

        line = next((l for l in sale.lines if l.id == line_id), None)
        if line is None:
            raise NotFoundError("ExchangeSaleLine", line_id)
        if line.is_fully_cancelled:
            raise BusinessRuleViolationError("Line is already fully cancelled")

        remaining_kg = line.quantity_kg - line.cancelled_kg
        if data.quantity_kg > remaining_kg:
            raise BusinessRuleViolationError(
                f"Cannot cancel {data.quantity_kg} kg — only {remaining_kg} kg remaining"
            )

        reversal_tx = await self.stock_repo.post_transaction(
            company_id=sale.company_id,
            warehouse_id=sale.warehouse_id,
            transaction_type=TransactionType.SHIPMENT_CANCEL_REVERSAL,
            direction=1,
            quantity_kg=data.quantity_kg,
            transaction_date=sale.sale_date,
            posted_by=ctx.actor_id,
            reference_type="EXCHANGE_SALE",
            reference_id=sale.id,
            reference_line_id=line.id,
            ginning_product_type=line.product_type,
            notes=data.reason,
        )

        line.cancelled_kg = line.cancelled_kg + data.quantity_kg
        line.is_fully_cancelled = (line.quantity_kg - line.cancelled_kg) <= Decimal("0")

        if line.is_fully_cancelled and line.bale_id is not None:
            bale = await self.bale_repo.get_by_id(line.bale_id)
            bale.status = GinningBaleStatus.IN_STOCK
            bale.sold_reference_type = None
            bale.sold_reference_id = None

        cancellation = ExchangeSaleCancellation(
            sale_id=sale.id,
            sale_line_id=line.id,
            quantity_kg=data.quantity_kg,
            reason=data.reason,
            reversal_transaction_id=reversal_tx.id,
            cancelled_by=ctx.actor_id,
        )
        await self.repo.save_cancellation(cancellation)

        all_fully_cancelled = all(l.is_fully_cancelled for l in sale.lines)
        any_cancelled = any(l.cancelled_kg > Decimal("0") for l in sale.lines)
        if all_fully_cancelled:
            sale.status = ExchangeSaleStatus.CANCELLED
        elif any_cancelled:
            sale.status = ExchangeSaleStatus.PARTIALLY_CANCELLED

        await self.repo.save(sale)
        sale = await self.repo.get_with_lines(sale.id, company_id)

        await self.audit.log(
            ctx=ctx, entity_type="exchange_sale", action=AuditAction.CANCEL,
            entity_id=sale.id, entity_display=sale.sale_number,
            after_data={"line_id": str(line_id), "cancelled_kg": str(data.quantity_kg)},
            reason=data.reason,
        )
        return sale
