from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError
from app.modules.audit.service import AuditService
from app.modules.counterparty.models import Counterparty
from app.modules.counterparty.repository import CounterpartyRepository
from app.modules.farmer_ledger.repository import FarmerLedgerRepository
from app.modules.farmer_settlement.models import FarmerPayment
from app.modules.farmer_settlement.repository import FarmerPaymentRepository
from app.modules.farmer_settlement.schemas import (
    FarmerBalanceResponse,
    FarmerLedgerEntryResponse,
    FarmerPaymentCancel,
    FarmerPaymentCreate,
    FarmerPaymentResponse,
)
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, CounterpartyType, FarmerLedgerEntryType, FarmerPaymentStatus
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_farmer_payment_number


class FarmerSettlementService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = FarmerPaymentRepository(session)
        self.counterparty_repo = CounterpartyRepository(session)
        self.ledger_repo = FarmerLedgerRepository(session)
        self.audit = AuditService(session)

    def build_response(self, payment: FarmerPayment) -> FarmerPaymentResponse:
        return FarmerPaymentResponse(
            id=payment.id,
            company_id=payment.company_id,
            farmer_id=payment.farmer_id,
            farmer_name=payment.farmer_name or "",
            payment_number=payment.payment_number,
            payment_date=payment.payment_date,
            amount=payment.amount,
            currency=payment.currency,
            payment_method=payment.payment_method,
            status=payment.status,
            posted_at=payment.posted_at,
            cancelled_at=payment.cancelled_at,
            cancel_reason=payment.cancel_reason,
            reference_note=payment.reference_note,
            created_at=payment.created_at,
        )

    async def list(
        self, company_id: uuid.UUID, page: int, page_size: int,
        farmer_id: uuid.UUID | None = None, status: FarmerPaymentStatus | None = None,
    ) -> PaginatedResponse[FarmerPaymentResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, farmer_id, status)
        return PaginatedResponse.build([self.build_response(p) for p in items], total, page, page_size)

    async def get(self, payment_id: uuid.UUID, company_id: uuid.UUID) -> FarmerPayment:
        return await self.repo.get_scoped_or_raise(payment_id, company_id, "FarmerPayment")

    async def create(
        self, company_id: uuid.UUID, data: FarmerPaymentCreate, ctx: AuditContext
    ) -> FarmerPayment:
        farmer = await self.counterparty_repo.get_scoped_or_raise(data.farmer_id, company_id, "Counterparty")

        payment_number = await generate_farmer_payment_number(self.session, company_id)
        payment = await self.repo.create(
            company_id=company_id,
            farmer_id=data.farmer_id,
            payment_number=payment_number,
            payment_date=data.payment_date,
            amount=data.amount,
            currency=data.currency,
            payment_method=data.payment_method,
            status=FarmerPaymentStatus.DRAFT,
            farmer_name=farmer.name,
            reference_note=data.reference_note,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx, entity_type="farmer_payment", action=AuditAction.CREATE,
            entity_id=payment.id, entity_display=payment.payment_number,
            after_data={"amount": str(data.amount), "farmer": farmer.name},
        )
        return payment

    async def post(self, payment_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext) -> FarmerPayment:
        payment = await self.get(payment_id, company_id)
        if payment.status != FarmerPaymentStatus.DRAFT:
            raise BusinessRuleViolationError("Only a DRAFT payment can be posted")

        ledger_entry = await self.ledger_repo.post_entry(
            company_id=company_id,
            farmer_id=payment.farmer_id,
            entry_type=FarmerLedgerEntryType.PAYMENT,
            direction=-1,
            amount=payment.amount,
            entry_date=payment.payment_date,
            posted_by=ctx.actor_id,
            reference_type="FARMER_PAYMENT",
            reference_id=payment.id,
            currency=payment.currency,
            farmer_name=payment.farmer_name,
            notes=f"Farmer payment {payment.payment_number}",
        )
        payment.status = FarmerPaymentStatus.POSTED
        payment.posted_at = datetime.now(timezone.utc)
        payment.posted_by = ctx.actor_id
        payment.ledger_entry_id = ledger_entry.id
        await self.repo.save(payment)

        await self.audit.log(
            ctx=ctx, entity_type="farmer_payment", action=AuditAction.POST,
            entity_id=payment.id, entity_display=payment.payment_number,
            after_data={"amount": str(payment.amount)},
        )
        return payment

    async def cancel(
        self, payment_id: uuid.UUID, company_id: uuid.UUID, data: FarmerPaymentCancel, ctx: AuditContext
    ) -> FarmerPayment:
        payment = await self.get(payment_id, company_id)
        if payment.status != FarmerPaymentStatus.POSTED:
            raise BusinessRuleViolationError("Only a POSTED payment can be cancelled")

        await self.ledger_repo.post_entry(
            company_id=company_id,
            farmer_id=payment.farmer_id,
            entry_type=FarmerLedgerEntryType.ADJUSTMENT,
            direction=1,
            amount=payment.amount,
            entry_date=payment.payment_date,
            posted_by=ctx.actor_id,
            reference_type="FARMER_PAYMENT",
            reference_id=payment.id,
            currency=payment.currency,
            farmer_name=payment.farmer_name,
            notes=f"CANCEL reversal of payment {payment.payment_number}: {data.reason}",
        )
        payment.status = FarmerPaymentStatus.CANCELLED
        payment.cancelled_at = datetime.now(timezone.utc)
        payment.cancelled_by = ctx.actor_id
        payment.cancel_reason = data.reason
        await self.repo.save(payment)

        await self.audit.log(
            ctx=ctx, entity_type="farmer_payment", action=AuditAction.CANCEL,
            entity_id=payment.id, entity_display=payment.payment_number, reason=data.reason,
        )
        return payment

    async def list_farmer_balances(self, company_id: uuid.UUID) -> list[FarmerBalanceResponse]:
        result = await self.session.execute(
            select(Counterparty).where(
                Counterparty.company_id == company_id,
                Counterparty.counterparty_type == CounterpartyType.FARMER,
            )
        )
        farmers = list(result.scalars().all())
        balances = await self.ledger_repo.get_balances_batch(company_id, [f.id for f in farmers])
        return [
            FarmerBalanceResponse(farmer_id=f.id, farmer_name=f.name, balance=balances.get(f.id, Decimal("0")))
            for f in farmers
        ]

    async def get_farmer_statement(
        self, company_id: uuid.UUID, farmer_id: uuid.UUID, page: int = 1, page_size: int = 100,
    ) -> PaginatedResponse[FarmerLedgerEntryResponse]:
        entries, total = await self.ledger_repo.get_entries(company_id, farmer_id, page=page, page_size=page_size)
        responses = [
            FarmerLedgerEntryResponse(
                id=e.id, entry_type=e.entry_type, direction=e.direction, amount=e.amount,
                currency=e.currency, reference_type=e.reference_type, reference_id=e.reference_id,
                entry_date=e.entry_date, notes=e.notes, created_at=e.created_at,
            )
            for e in entries
        ]
        return PaginatedResponse.build(responses, total, page, page_size)
