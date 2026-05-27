import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, BusinessRuleViolationError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.counterparty.models import Counterparty, CounterpartyContact
from app.modules.counterparty.repository import (
    CounterpartyContactRepository,
    CounterpartyRepository,
)
from app.modules.counterparty.schemas import ContactCreate, CounterpartyCreate, CounterpartyUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, CounterpartyType
from app.shared.schemas import PaginatedResponse


class CounterpartyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CounterpartyRepository(session)
        self.contact_repo = CounterpartyContactRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        counterparty_type: CounterpartyType | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[Counterparty]:
        items, total = await self.repo.list_paginated(
            company_id, page, page_size, active_only, counterparty_type, search
        )
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, counterparty_id: uuid.UUID) -> Counterparty:
        cp = await self.repo.get_with_contacts(counterparty_id)
        if cp is None:
            raise NotFoundError("Counterparty", counterparty_id)
        return cp

    async def create(
        self, company_id: uuid.UUID, data: CounterpartyCreate, ctx: AuditContext
    ) -> Counterparty:
        if data.tax_id:
            existing = await self.repo.get_by_tax_id(company_id, data.tax_id)
            if existing:
                raise AlreadyExistsError("Counterparty", "tax_id")

        cp = await self.repo.create(
            company_id=company_id,
            name=data.name,
            short_name=data.short_name,
            country=data.country,
            tax_id=data.tax_id,
            counterparty_type=data.counterparty_type,
            notes=data.notes,
            created_by=ctx.actor_id,
        )
        for contact_data in data.contacts:
            await self.contact_repo.create(
                counterparty_id=cp.id,
                contact_type=contact_data.contact_type,
                contact_value=contact_data.contact_value,
                label=contact_data.label,
                is_primary=contact_data.is_primary,
            )

        await self.audit.log(
            ctx=ctx,
            entity_type="counterparty",
            action=AuditAction.CREATE,
            entity_id=cp.id,
            entity_display=cp.name,
            after_data={"name": cp.name, "tax_id": cp.tax_id, "type": cp.counterparty_type.value},
        )
        # Re-fetch with contacts for return
        return await self.get(cp.id)

    async def update(
        self, counterparty_id: uuid.UUID, data: CounterpartyUpdate, ctx: AuditContext
    ) -> Counterparty:
        cp = await self.repo.get_by_id_or_raise(counterparty_id, "Counterparty")
        before = {"name": cp.name, "tax_id": cp.tax_id}

        if data.tax_id is not None and data.tax_id != cp.tax_id:
            existing = await self.repo.get_by_tax_id(cp.company_id, data.tax_id)
            if existing and existing.id != counterparty_id:
                raise AlreadyExistsError("Counterparty", "tax_id")

        if data.name is not None:
            cp.name = data.name
        if data.short_name is not None:
            cp.short_name = data.short_name
        if data.country is not None:
            cp.country = data.country
        if data.tax_id is not None:
            cp.tax_id = data.tax_id
        if data.counterparty_type is not None:
            cp.counterparty_type = data.counterparty_type
        if data.notes is not None:
            cp.notes = data.notes

        await self.repo.save(cp)
        await self.audit.log(
            ctx=ctx,
            entity_type="counterparty",
            action=AuditAction.UPDATE,
            entity_id=cp.id,
            entity_display=cp.name,
            before_data=before,
            after_data={"name": cp.name, "tax_id": cp.tax_id},
        )
        return await self.get(cp.id)

    async def add_contact(
        self, counterparty_id: uuid.UUID, data: ContactCreate, ctx: AuditContext
    ) -> CounterpartyContact:
        cp = await self.repo.get_by_id_or_raise(counterparty_id, "Counterparty")
        contact = await self.contact_repo.create(
            counterparty_id=cp.id,
            contact_type=data.contact_type,
            contact_value=data.contact_value,
            label=data.label,
            is_primary=data.is_primary,
        )
        return contact

    async def remove_contact(
        self, counterparty_id: uuid.UUID, contact_id: uuid.UUID, ctx: AuditContext
    ) -> None:
        contact = await self.contact_repo.get_by_id_or_raise(contact_id, "CounterpartyContact")
        if contact.counterparty_id != counterparty_id:
            raise NotFoundError("CounterpartyContact", contact_id)
        await self.contact_repo.delete(contact)

    async def _set_active(
        self, counterparty_id: uuid.UUID, is_active: bool, ctx: AuditContext
    ) -> Counterparty:
        cp = await self.repo.get_by_id_or_raise(counterparty_id, "Counterparty")
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        cp.is_active = is_active
        await self.repo.save(cp)
        await self.audit.log(
            ctx=ctx,
            entity_type="counterparty",
            action=action,
            entity_id=cp.id,
            entity_display=cp.name,
        )
        return await self.get(cp.id)

    async def activate(self, counterparty_id: uuid.UUID, ctx: AuditContext) -> Counterparty:
        return await self._set_active(counterparty_id, True, ctx)

    async def deactivate(self, counterparty_id: uuid.UUID, ctx: AuditContext) -> Counterparty:
        return await self._set_active(counterparty_id, False, ctx)

    async def merge(
        self,
        target_id: uuid.UUID,
        source_id: uuid.UUID,
        ctx: AuditContext,
        reason: str | None = None,
    ) -> Counterparty:
        """
        Merge source into target. All FK references to source are re-pointed to target.
        Source is then deactivated with merged_into_id = target.id.
        Uses raw UPDATE statements to avoid importing every downstream model.
        """
        target = await self.repo.get_by_id_or_raise(target_id, "Counterparty")
        source = await self.repo.get_by_id_or_raise(source_id, "Counterparty")

        if not target.is_active:
            raise BusinessRuleViolationError("Target counterparty is not active")
        if source.id == target.id:
            raise BusinessRuleViolationError("Cannot merge a counterparty into itself")
        if source.merged_into_id is not None:
            raise BusinessRuleViolationError("Source counterparty has already been merged")

        src = source.id
        tgt = target.id

        # Re-point all FK references atomically within the caller's transaction
        await self.session.execute(
            text("UPDATE stock_transactions SET owner_id = :tgt, owner_name = :tgt_name WHERE owner_id = :src"),
            {"tgt": tgt, "tgt_name": target.name, "src": src},
        )
        await self.session.execute(
            text("UPDATE shipment_lines SET owner_id = :tgt WHERE owner_id = :src"),
            {"tgt": tgt, "src": src},
        )
        await self.session.execute(
            text("UPDATE shipments SET buyer_id = :tgt WHERE buyer_id = :src"),
            {"tgt": tgt, "src": src},
        )
        await self.session.execute(
            text("UPDATE contracts SET counterparty_id = :tgt WHERE counterparty_id = :src"),
            {"tgt": tgt, "src": src},
        )
        await self.session.execute(
            text("UPDATE daily_report_lines SET owner_id = :tgt WHERE owner_id = :src"),
            {"tgt": tgt, "src": src},
        )
        await self.session.execute(
            text("UPDATE daily_report_lines SET buyer_id = :tgt WHERE buyer_id = :src"),
            {"tgt": tgt, "src": src},
        )
        await self.session.execute(
            text("UPDATE inventory_adjustment_lines SET owner_id = :tgt WHERE owner_id = :src"),
            {"tgt": tgt, "src": src},
        )

        source.is_active = False
        source.merged_into_id = tgt
        await self.repo.save(source)

        await self.audit.log(
            ctx=ctx,
            entity_type="counterparty",
            action=AuditAction.MERGE,
            entity_id=tgt,
            entity_display=target.name,
            before_data={"source_id": str(src), "source_name": source.name},
            after_data={"target_id": str(tgt), "target_name": target.name},
            reason=reason,
        )
        return await self.get(tgt)
