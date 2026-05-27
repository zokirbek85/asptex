import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, NotFoundError
from app.modules.audit.service import AuditService
from app.modules.contract.models import Contract
from app.modules.contract.repository import ContractRepository
from app.modules.contract.schemas import ContractCreate, ContractUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction
from app.shared.schemas import PaginatedResponse


class ContractService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ContractRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        active_only: bool = False,
        counterparty_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> PaginatedResponse[Contract]:
        items, total = await self.repo.list_paginated(
            company_id, page, page_size, active_only, counterparty_id, search
        )
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, contract_id: uuid.UUID) -> Contract:
        contract = await self.repo.get_with_counterparty(contract_id)
        if contract is None:
            raise NotFoundError("Contract", contract_id)
        return contract

    async def create(
        self, company_id: uuid.UUID, data: ContractCreate, ctx: AuditContext
    ) -> Contract:
        existing = await self.repo.get_by_number(company_id, data.contract_number)
        if existing:
            raise AlreadyExistsError("Contract", "contract_number")

        contract = await self.repo.create(
            company_id=company_id,
            contract_number=data.contract_number,
            contract_date=data.contract_date,
            counterparty_id=data.counterparty_id,
            description=data.description,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="contract",
            action=AuditAction.CREATE,
            entity_id=contract.id,
            entity_display=contract.contract_number,
            after_data={
                "contract_number": contract.contract_number,
                "counterparty_id": str(data.counterparty_id),
            },
        )
        return await self.get(contract.id)

    async def update(
        self, contract_id: uuid.UUID, data: ContractUpdate, ctx: AuditContext
    ) -> Contract:
        contract = await self.repo.get_with_counterparty(contract_id)
        if contract is None:
            raise NotFoundError("Contract", contract_id)

        before = {
            "contract_number": contract.contract_number,
            "contract_date": str(contract.contract_date),
        }

        if data.contract_number is not None and data.contract_number != contract.contract_number:
            existing = await self.repo.get_by_number(contract.company_id, data.contract_number)
            if existing and existing.id != contract_id:
                raise AlreadyExistsError("Contract", "contract_number")
            contract.contract_number = data.contract_number

        if data.contract_date is not None:
            contract.contract_date = data.contract_date
        if data.description is not None:
            contract.description = data.description

        await self.repo.save(contract)
        await self.audit.log(
            ctx=ctx,
            entity_type="contract",
            action=AuditAction.UPDATE,
            entity_id=contract.id,
            entity_display=contract.contract_number,
            before_data=before,
            after_data={"contract_number": contract.contract_number},
        )
        return await self.get(contract.id)

    async def _set_active(
        self, contract_id: uuid.UUID, is_active: bool, ctx: AuditContext
    ) -> Contract:
        contract = await self.repo.get_with_counterparty(contract_id)
        if contract is None:
            raise NotFoundError("Contract", contract_id)
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        contract.is_active = is_active
        await self.repo.save(contract)
        await self.audit.log(
            ctx=ctx,
            entity_type="contract",
            action=action,
            entity_id=contract.id,
            entity_display=contract.contract_number,
        )
        return contract

    async def activate(self, contract_id: uuid.UUID, ctx: AuditContext) -> Contract:
        return await self._set_active(contract_id, True, ctx)

    async def deactivate(self, contract_id: uuid.UUID, ctx: AuditContext) -> Contract:
        return await self._set_active(contract_id, False, ctx)
