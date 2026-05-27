import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.count_catalog.models import CountCatalog
from app.modules.count_catalog.repository import CountCatalogRepository
from app.modules.count_catalog.schemas import CountCreate, CountUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction
from app.shared.schemas import PaginatedResponse


class CountCatalogService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CountCatalogRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        search: str | None = None,
    ) -> PaginatedResponse[CountCatalog]:
        items, total = await self.repo.list_paginated(
            company_id, page, page_size, active_only, search
        )
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, count_id: uuid.UUID) -> CountCatalog:
        return await self.repo.get_by_id_or_raise(count_id, "CountCatalog")

    async def create(
        self, company_id: uuid.UUID, data: CountCreate, ctx: AuditContext
    ) -> CountCatalog:
        if await self.repo.get_by_value(company_id, data.count_value):
            raise AlreadyExistsError("CountCatalog", "count_value")

        count = await self.repo.create(
            company_id=company_id,
            count_value=data.count_value,
            yarn_type=data.yarn_type,
            composition=data.composition,
            description=data.description,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="count_catalog",
            action=AuditAction.CREATE,
            entity_id=count.id,
            entity_display=count.count_value,
            after_data={"count_value": count.count_value, "yarn_type": count.yarn_type},
        )
        return count

    async def update(
        self, count_id: uuid.UUID, data: CountUpdate, ctx: AuditContext
    ) -> CountCatalog:
        count = await self.repo.get_by_id_or_raise(count_id, "CountCatalog")
        before = {"yarn_type": count.yarn_type, "composition": count.composition}

        if data.yarn_type is not None:
            count.yarn_type = data.yarn_type
        if data.composition is not None:
            count.composition = data.composition
        if data.description is not None:
            count.description = data.description

        await self.repo.save(count)
        await self.audit.log(
            ctx=ctx,
            entity_type="count_catalog",
            action=AuditAction.UPDATE,
            entity_id=count.id,
            entity_display=count.count_value,
            before_data=before,
            after_data={"yarn_type": count.yarn_type},
        )
        return count

    async def _set_active(
        self, count_id: uuid.UUID, is_active: bool, ctx: AuditContext
    ) -> CountCatalog:
        count = await self.repo.get_by_id_or_raise(count_id, "CountCatalog")
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        count.is_active = is_active
        await self.repo.save(count)
        await self.audit.log(
            ctx=ctx,
            entity_type="count_catalog",
            action=action,
            entity_id=count.id,
            entity_display=count.count_value,
        )
        return count

    async def activate(self, count_id: uuid.UUID, ctx: AuditContext) -> CountCatalog:
        return await self._set_active(count_id, True, ctx)

    async def deactivate(self, count_id: uuid.UUID, ctx: AuditContext) -> CountCatalog:
        return await self._set_active(count_id, False, ctx)
