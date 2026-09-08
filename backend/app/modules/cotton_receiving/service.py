from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.cotton_receiving.models import CottonReceiving
from app.modules.cotton_receiving.repository import CottonPriceListRepository, CottonReceivingRepository
from app.modules.cotton_receiving.schemas import (
    CottonPriceListCreate,
    CottonReceivingCancel,
    CottonReceivingCreate,
    CottonReceivingResponse,
    CottonReceivingUpdate,
)
from app.modules.counterparty.repository import CounterpartyRepository
from app.modules.farmer_ledger.repository import FarmerLedgerRepository
from app.modules.ginning_bunt.repository import GinningBuntRepository
from app.modules.stock.repository import StockRepository
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, BuntStatus, CottonReceivingStatus, FarmerLedgerEntryType, TransactionType
from app.shared.schemas import PaginatedResponse
from app.shared.utils.lot_number import generate_cotton_receiving_number


class CottonReceivingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CottonReceivingRepository(session)
        self.price_repo = CottonPriceListRepository(session)
        self.bunt_repo = GinningBuntRepository(session)
        self.counterparty_repo = CounterpartyRepository(session)
        self.stock_repo = StockRepository(session)
        self.ledger_repo = FarmerLedgerRepository(session)
        self.audit = AuditService(session)

    def build_response(self, r: CottonReceiving, bunt_lot_number: str) -> CottonReceivingResponse:
        return CottonReceivingResponse(
            id=r.id,
            company_id=r.company_id,
            bunt_id=r.bunt_id,
            bunt_lot_number=bunt_lot_number,
            farmer_id=r.farmer_id,
            farmer_name=r.farmer_name or "",
            contract_id=r.contract_id,
            receiving_number=r.receiving_number,
            receiving_date=r.receiving_date,
            vehicle_number=r.vehicle_number,
            driver_name=r.driver_name,
            gross_weight_kg=r.gross_weight_kg,
            tare_weight_kg=r.tare_weight_kg,
            net_weight_kg=r.net_weight_kg,
            moisture_pct=r.moisture_pct,
            contamination_pct=r.contamination_pct,
            grade=r.grade,
            variety=r.variety,
            sort=r.sort,
            quality_class=r.quality_class,
            unit_price=r.unit_price,
            price_source=r.price_source,
            total_amount=r.total_amount,
            currency=r.currency,
            status=r.status,
            posted_at=r.posted_at,
            cancelled_at=r.cancelled_at,
            cancel_reason=r.cancel_reason,
            notes=r.notes,
            created_at=r.created_at,
        )

    async def bunt_lot_number(self, bunt_id: uuid.UUID, company_id: uuid.UUID) -> str:
        bunt = await self.bunt_repo.get_scoped_with_lot(bunt_id, company_id)
        return bunt.lot.lot_number if bunt else ""

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        bunt_id: uuid.UUID | None = None,
        farmer_id: uuid.UUID | None = None,
        status: CottonReceivingStatus | None = None,
    ) -> PaginatedResponse[CottonReceivingResponse]:
        items, total = await self.repo.list_paginated(company_id, page, page_size, bunt_id, farmer_id, status)
        responses = []
        bunt_number_cache: dict[uuid.UUID, str] = {}
        for r in items:
            if r.bunt_id not in bunt_number_cache:
                bunt_number_cache[r.bunt_id] = await self.bunt_lot_number(r.bunt_id, company_id)
            responses.append(self.build_response(r, bunt_number_cache[r.bunt_id]))
        return PaginatedResponse.build(responses, total, page, page_size)

    async def get(self, receiving_id: uuid.UUID, company_id: uuid.UUID) -> CottonReceiving:
        r = await self.repo.get_scoped_or_raise(receiving_id, company_id, "CottonReceiving")
        return r

    async def create(
        self, company_id: uuid.UUID, data: CottonReceivingCreate, ctx: AuditContext
    ) -> CottonReceiving:
        bunt = await self.bunt_repo.get_scoped_with_lot(data.bunt_id, company_id)
        if bunt is None:
            raise NotFoundError("GinningBunt", data.bunt_id)
        if bunt.status != BuntStatus.OPEN:
            raise BusinessRuleViolationError("Cannot receive cotton into a CLOSED bunt")

        farmer = await self.counterparty_repo.get_scoped_or_raise(data.farmer_id, company_id, "Counterparty")

        net_weight_kg = data.gross_weight_kg - data.tare_weight_kg

        unit_price = data.unit_price
        price_source = "MANUAL" if unit_price is not None else None
        if unit_price is None:
            rule = await self.price_repo.find_best_match(
                company_id, data.receiving_date, data.grade, data.variety, data.sort, data.quality_class
            )
            if rule is not None:
                unit_price = rule.price_per_kg
                price_source = "PRICE_LIST"

        total_amount = (net_weight_kg * unit_price) if unit_price is not None else None

        receiving_number = await generate_cotton_receiving_number(self.session, company_id)

        receiving = await self.repo.create(
            company_id=company_id,
            bunt_id=data.bunt_id,
            farmer_id=data.farmer_id,
            contract_id=data.contract_id,
            receiving_number=receiving_number,
            receiving_date=data.receiving_date,
            vehicle_number=data.vehicle_number,
            driver_name=data.driver_name,
            gross_weight_kg=data.gross_weight_kg,
            tare_weight_kg=data.tare_weight_kg,
            net_weight_kg=net_weight_kg,
            moisture_pct=data.moisture_pct,
            contamination_pct=data.contamination_pct,
            grade=data.grade,
            variety=data.variety,
            sort=data.sort,
            quality_class=data.quality_class,
            unit_price=unit_price,
            price_source=price_source,
            total_amount=total_amount,
            currency=data.currency,
            status=CottonReceivingStatus.DRAFT,
            farmer_name=farmer.name,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="cotton_receiving",
            action=AuditAction.CREATE,
            entity_id=receiving.id,
            entity_display=receiving.receiving_number,
            after_data={"net_weight_kg": str(net_weight_kg), "farmer": farmer.name},
        )
        return receiving

    async def update(
        self, receiving_id: uuid.UUID, company_id: uuid.UUID, data: CottonReceivingUpdate, ctx: AuditContext
    ) -> CottonReceiving:
        receiving = await self.get(receiving_id, company_id)
        if receiving.status != CottonReceivingStatus.DRAFT:
            raise BusinessRuleViolationError("Only a DRAFT receiving can be edited")

        for field in (
            "contract_id", "vehicle_number", "driver_name", "moisture_pct", "contamination_pct",
            "grade", "variety", "sort", "quality_class", "unit_price", "notes",
        ):
            value = getattr(data, field)
            if value is not None:
                setattr(receiving, field, value)
        if data.unit_price is not None:
            receiving.price_source = "MANUAL"

        if data.gross_weight_kg is not None:
            receiving.gross_weight_kg = data.gross_weight_kg
        if data.tare_weight_kg is not None:
            receiving.tare_weight_kg = data.tare_weight_kg
        if data.gross_weight_kg is not None or data.tare_weight_kg is not None:
            if receiving.tare_weight_kg >= receiving.gross_weight_kg:
                raise BusinessRuleViolationError("tare_weight_kg must be less than gross_weight_kg")
            receiving.net_weight_kg = receiving.gross_weight_kg - receiving.tare_weight_kg

        if receiving.unit_price is not None:
            receiving.total_amount = receiving.net_weight_kg * receiving.unit_price

        await self.repo.save(receiving)
        return receiving

    async def post(self, receiving_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext) -> CottonReceiving:
        receiving = await self.get(receiving_id, company_id)
        if receiving.status != CottonReceivingStatus.DRAFT:
            raise BusinessRuleViolationError("Only a DRAFT receiving can be posted")
        if receiving.unit_price is None:
            raise BusinessRuleViolationError("unit_price must be set before posting")

        bunt = await self.bunt_repo.get_scoped_with_lot(receiving.bunt_id, company_id)
        if bunt is None:
            raise NotFoundError("GinningBunt", receiving.bunt_id)
        if bunt.status != BuntStatus.OPEN:
            raise BusinessRuleViolationError("Cannot post a receiving into a CLOSED bunt")

        tx = await self.stock_repo.post_transaction(
            company_id=company_id,
            warehouse_id=bunt.warehouse_id,
            transaction_type=TransactionType.RECEIPT,
            direction=1,
            quantity_kg=receiving.net_weight_kg,
            transaction_date=receiving.receiving_date,
            posted_by=ctx.actor_id,
            reference_type="COTTON_RECEIVING",
            reference_id=receiving.id,
            lot_id=bunt.lot_id,
            owner_id=None,
            lot_number=bunt.lot.lot_number,
            notes=f"Cotton receiving {receiving.receiving_number}",
        )

        ledger_entry = await self.ledger_repo.post_entry(
            company_id=company_id,
            farmer_id=receiving.farmer_id,
            entry_type=FarmerLedgerEntryType.RECEIVABLE_COTTON,
            direction=1,
            amount=receiving.total_amount,
            entry_date=receiving.receiving_date,
            posted_by=ctx.actor_id,
            reference_type="COTTON_RECEIVING",
            reference_id=receiving.id,
            currency=receiving.currency,
            farmer_name=receiving.farmer_name,
            notes=f"Cotton receiving {receiving.receiving_number}",
        )

        receiving.status = CottonReceivingStatus.POSTED
        receiving.posted_at = datetime.now(timezone.utc)
        receiving.posted_by = ctx.actor_id
        receiving.transaction_id = tx.id
        receiving.ledger_entry_id = ledger_entry.id
        await self.repo.save(receiving)

        await self.audit.log(
            ctx=ctx,
            entity_type="cotton_receiving",
            action=AuditAction.POST,
            entity_id=receiving.id,
            entity_display=receiving.receiving_number,
            after_data={"net_weight_kg": str(receiving.net_weight_kg), "total_amount": str(receiving.total_amount)},
        )
        return receiving

    async def cancel(
        self, receiving_id: uuid.UUID, company_id: uuid.UUID, data: CottonReceivingCancel, ctx: AuditContext
    ) -> CottonReceiving:
        receiving = await self.get(receiving_id, company_id)
        if receiving.status != CottonReceivingStatus.POSTED:
            raise BusinessRuleViolationError("Only a POSTED receiving can be cancelled")

        bunt = await self.bunt_repo.get_scoped_with_lot(receiving.bunt_id, company_id)
        current_balance = await self.stock_repo.get_balance(
            company_id=company_id, warehouse_id=bunt.warehouse_id, lot_id=bunt.lot_id, owner_id=None,
        )
        if current_balance < receiving.net_weight_kg:
            raise BusinessRuleViolationError(
                "Cannot cancel: bunt has already been partially consumed by production"
            )

        await self.stock_repo.post_transaction(
            company_id=company_id,
            warehouse_id=bunt.warehouse_id,
            transaction_type=TransactionType.RECEIPT,
            direction=-1,
            quantity_kg=receiving.net_weight_kg,
            transaction_date=receiving.receiving_date,
            posted_by=ctx.actor_id,
            reference_type="COTTON_RECEIVING",
            reference_id=receiving.id,
            lot_id=bunt.lot_id,
            owner_id=None,
            lot_number=bunt.lot.lot_number,
            notes=f"CANCEL reversal of receiving {receiving.receiving_number}: {data.reason}",
        )
        await self.ledger_repo.post_entry(
            company_id=company_id,
            farmer_id=receiving.farmer_id,
            entry_type=FarmerLedgerEntryType.ADJUSTMENT,
            direction=-1,
            amount=receiving.total_amount,
            entry_date=receiving.receiving_date,
            posted_by=ctx.actor_id,
            reference_type="COTTON_RECEIVING",
            reference_id=receiving.id,
            currency=receiving.currency,
            farmer_name=receiving.farmer_name,
            notes=f"CANCEL reversal of receiving {receiving.receiving_number}: {data.reason}",
        )

        receiving.status = CottonReceivingStatus.CANCELLED
        receiving.cancelled_at = datetime.now(timezone.utc)
        receiving.cancelled_by = ctx.actor_id
        receiving.cancel_reason = data.reason
        await self.repo.save(receiving)

        await self.audit.log(
            ctx=ctx,
            entity_type="cotton_receiving",
            action=AuditAction.CANCEL,
            entity_id=receiving.id,
            entity_display=receiving.receiving_number,
            reason=data.reason,
        )
        return receiving

    async def list_price_rules(self, company_id: uuid.UUID):
        from sqlalchemy import select

        from app.modules.cotton_receiving.models import CottonPriceList

        result = await self.session.execute(
            select(CottonPriceList)
            .where(CottonPriceList.company_id == company_id)
            .order_by(CottonPriceList.effective_from.desc())
        )
        return list(result.scalars().all())

    async def create_price_rule(self, company_id: uuid.UUID, data: CottonPriceListCreate, ctx: AuditContext):
        rule = await self.price_repo.create(
            company_id=company_id,
            grade=data.grade,
            variety=data.variety,
            sort=data.sort,
            quality_class=data.quality_class,
            price_per_kg=data.price_per_kg,
            currency=data.currency,
            effective_from=data.effective_from,
            is_active=True,
            created_by=ctx.actor_id,
        )
        return rule
