import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.company.models import Company
from app.modules.company.repository import CompanyRepository
from app.modules.company.schemas import CompanyCreate, CompanyUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction
from app.shared.schemas import PaginatedResponse


class CompanyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CompanyRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        page: int,
        page_size: int,
        active_only: bool = False,
        search: str | None = None,
    ) -> PaginatedResponse:
        items, total = await self.repo.list_paginated(page, page_size, active_only, search)
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, company_id: uuid.UUID) -> Company:
        return await self.repo.get_by_id_or_raise(company_id, "Company")

    async def create(self, data: CompanyCreate, ctx: AuditContext) -> Company:
        if data.tax_id:
            existing = await self.repo.get_by_tax_id(data.tax_id)
            if existing:
                raise AlreadyExistsError("Company", "tax_id")

        company = await self.repo.create(
            name=data.name,
            short_name=data.short_name,
            tax_id=data.tax_id,
            address=data.address,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="company",
            action=AuditAction.CREATE,
            entity_id=company.id,
            entity_display=company.name,
            after_data={"name": company.name, "tax_id": company.tax_id},
        )
        return company

    async def update(self, company_id: uuid.UUID, data: CompanyUpdate, ctx: AuditContext) -> Company:
        company = await self.repo.get_by_id_or_raise(company_id, "Company")
        before = {"name": company.name, "tax_id": company.tax_id, "address": company.address}

        if data.tax_id and data.tax_id != company.tax_id:
            existing = await self.repo.get_by_tax_id(data.tax_id)
            if existing and existing.id != company_id:
                raise AlreadyExistsError("Company", "tax_id")

        if data.name is not None:
            company.name = data.name
        if data.short_name is not None:
            company.short_name = data.short_name
        if data.tax_id is not None:
            company.tax_id = data.tax_id
        if data.address is not None:
            company.address = data.address

        await self.repo.save(company)
        await self.audit.log(
            ctx=ctx,
            entity_type="company",
            action=AuditAction.UPDATE,
            entity_id=company.id,
            entity_display=company.name,
            before_data=before,
            after_data={"name": company.name, "tax_id": company.tax_id},
        )
        return company

    async def _set_active(
        self, company_id: uuid.UUID, is_active: bool, ctx: AuditContext
    ) -> Company:
        company = await self.repo.get_by_id_or_raise(company_id, "Company")
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        company.is_active = is_active
        await self.repo.save(company)
        await self.audit.log(
            ctx=ctx, entity_type="company", action=action,
            entity_id=company.id, entity_display=company.name,
        )
        return company

    async def activate(self, company_id: uuid.UUID, ctx: AuditContext) -> Company:
        return await self._set_active(company_id, True, ctx)

    async def deactivate(self, company_id: uuid.UUID, ctx: AuditContext) -> Company:
        return await self._set_active(company_id, False, ctx)
