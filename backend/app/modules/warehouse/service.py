import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.warehouse.models import Warehouse
from app.modules.warehouse.repository import WarehouseRepository
from app.modules.warehouse.schemas import WarehouseCreate, WarehouseUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction, WarehouseType
from app.shared.schemas import PaginatedResponse


class WarehouseService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = WarehouseRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        warehouse_type: WarehouseType | None = None,
    ) -> PaginatedResponse[Warehouse]:
        items, total = await self.repo.list_paginated(
            company_id, page, page_size, active_only, warehouse_type
        )
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, warehouse_id: uuid.UUID) -> Warehouse:
        return await self.repo.get_by_id_or_raise(warehouse_id, "Warehouse")

    async def create(
        self, company_id: uuid.UUID, data: WarehouseCreate, ctx: AuditContext
    ) -> Warehouse:
        if await self.repo.get_by_code(company_id, data.code):
            raise AlreadyExistsError("Warehouse", "code")

        warehouse = await self.repo.create(
            company_id=company_id,
            code=data.code,
            name=data.name,
            warehouse_type=data.warehouse_type,
            description=data.description,
            sort_order=data.sort_order,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="warehouse",
            action=AuditAction.CREATE,
            entity_id=warehouse.id,
            entity_display=warehouse.name,
            after_data={
                "code": warehouse.code,
                "name": warehouse.name,
                "type": warehouse.warehouse_type.value,
            },
        )
        return warehouse

    async def update(
        self, warehouse_id: uuid.UUID, data: WarehouseUpdate, ctx: AuditContext
    ) -> Warehouse:
        warehouse = await self.repo.get_by_id_or_raise(warehouse_id, "Warehouse")
        before = {"name": warehouse.name, "description": warehouse.description}

        if data.name is not None:
            warehouse.name = data.name
        if data.description is not None:
            warehouse.description = data.description
        if data.sort_order is not None:
            warehouse.sort_order = data.sort_order

        await self.repo.save(warehouse)
        await self.audit.log(
            ctx=ctx,
            entity_type="warehouse",
            action=AuditAction.UPDATE,
            entity_id=warehouse.id,
            entity_display=warehouse.name,
            before_data=before,
            after_data={"name": warehouse.name},
        )
        return warehouse

    async def _set_active(
        self, warehouse_id: uuid.UUID, is_active: bool, ctx: AuditContext
    ) -> Warehouse:
        warehouse = await self.repo.get_by_id_or_raise(warehouse_id, "Warehouse")
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        warehouse.is_active = is_active
        await self.repo.save(warehouse)
        await self.audit.log(
            ctx=ctx,
            entity_type="warehouse",
            action=action,
            entity_id=warehouse.id,
            entity_display=warehouse.name,
        )
        return warehouse

    async def activate(self, warehouse_id: uuid.UUID, ctx: AuditContext) -> Warehouse:
        return await self._set_active(warehouse_id, True, ctx)

    async def deactivate(self, warehouse_id: uuid.UUID, ctx: AuditContext) -> Warehouse:
        return await self._set_active(warehouse_id, False, ctx)
