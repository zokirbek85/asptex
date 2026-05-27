import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AlreadyExistsError, BusinessRuleViolationError, NotFoundError
from app.core.security import hash_password
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.user.models import UserCompanyRole
from app.modules.user.repository import UserCompanyRoleRepository, UserManagementRepository
from app.modules.user.schemas import UserCreate, UserRoleAssign, UserRoleUpdate, UserUpdate
from app.shared.base_service import AuditContext
from app.shared.enums import AuditAction
from app.shared.schemas import PaginatedResponse


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = UserManagementRepository(session)
        self.role_repo = UserCompanyRoleRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        page: int,
        page_size: int,
        active_only: bool = False,
        search: str | None = None,
    ) -> PaginatedResponse[User]:
        items, total = await self.repo.list_paginated(page, page_size, active_only, search)
        return PaginatedResponse.build(items, total, page, page_size)

    async def get(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_with_roles(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        return user

    async def create(self, data: UserCreate, ctx: AuditContext) -> User:
        if await self.repo.get_by_username(data.username):
            raise AlreadyExistsError("User", "username")
        if data.email and await self.repo.get_by_email(data.email):
            raise AlreadyExistsError("User", "email")

        user = await self.repo.create(
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            preferred_language=data.preferred_language,
            is_superadmin=data.is_superadmin,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="user",
            action=AuditAction.CREATE,
            entity_id=user.id,
            entity_display=user.username,
            after_data={"username": user.username, "full_name": user.full_name},
        )
        return user

    async def update(self, user_id: uuid.UUID, data: UserUpdate, ctx: AuditContext) -> User:
        user = await self.repo.get_with_roles(user_id)
        if user is None:
            raise NotFoundError("User", user_id)

        before = {"full_name": user.full_name, "email": user.email}

        if data.email is not None and data.email != user.email:
            existing = await self.repo.get_by_email(data.email)
            if existing and existing.id != user_id:
                raise AlreadyExistsError("User", "email")
            user.email = data.email

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.preferred_language is not None:
            user.preferred_language = data.preferred_language

        await self.repo.save(user)
        await self.audit.log(
            ctx=ctx,
            entity_type="user",
            action=AuditAction.UPDATE,
            entity_id=user.id,
            entity_display=user.username,
            before_data=before,
            after_data={"full_name": user.full_name, "email": user.email},
        )
        return user

    async def change_password(
        self, user_id: uuid.UUID, new_password: str, ctx: AuditContext
    ) -> None:
        user = await self.repo.get_by_id_or_raise(user_id, "User")
        user.hashed_password = hash_password(new_password)
        await self.repo.save(user)
        await self.audit.log(
            ctx=ctx,
            entity_type="user",
            action=AuditAction.UPDATE,
            entity_id=user.id,
            entity_display=user.username,
            after_data={"action": "password_changed"},
        )

    async def _set_active(
        self, user_id: uuid.UUID, is_active: bool, ctx: AuditContext
    ) -> User:
        user = await self.repo.get_with_roles(user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        action = AuditAction.ACTIVATE if is_active else AuditAction.DEACTIVATE
        user.is_active = is_active
        await self.repo.save(user)
        await self.audit.log(
            ctx=ctx,
            entity_type="user",
            action=action,
            entity_id=user.id,
            entity_display=user.username,
        )
        return user

    async def activate(self, user_id: uuid.UUID, ctx: AuditContext) -> User:
        return await self._set_active(user_id, True, ctx)

    async def deactivate(self, user_id: uuid.UUID, ctx: AuditContext) -> User:
        return await self._set_active(user_id, False, ctx)

    async def assign_role(
        self, user_id: uuid.UUID, data: UserRoleAssign, ctx: AuditContext
    ) -> UserCompanyRole:
        user = await self.repo.get_by_id_or_raise(user_id, "User")
        existing = await self.role_repo.get_role(user_id, data.company_id)
        if existing:
            raise BusinessRuleViolationError(
                "User already has a role in this company. Use update to change it."
            )

        role = await self.role_repo.create(
            user_id=user_id,
            company_id=data.company_id,
            role=data.role,
            warehouse_id=data.warehouse_id,
            created_by=ctx.actor_id,
        )
        await self.audit.log(
            ctx=ctx,
            entity_type="user_role",
            action=AuditAction.CREATE,
            entity_id=role.id,
            entity_display=f"{user.username} → {data.role.value}",
            after_data={
                "user_id": str(user_id),
                "company_id": str(data.company_id),
                "role": data.role.value,
            },
        )
        return role

    async def update_role(
        self,
        user_id: uuid.UUID,
        company_id: uuid.UUID,
        data: UserRoleUpdate,
        ctx: AuditContext,
    ) -> UserCompanyRole:
        user = await self.repo.get_by_id_or_raise(user_id, "User")
        role = await self.role_repo.get_role(user_id, company_id)
        if role is None:
            raise NotFoundError("UserCompanyRole", f"{user_id}/{company_id}")

        before = {"role": role.role.value, "warehouse_id": str(role.warehouse_id) if role.warehouse_id else None}
        role.role = data.role
        role.warehouse_id = data.warehouse_id
        await self.role_repo.save(role)
        await self.audit.log(
            ctx=ctx,
            entity_type="user_role",
            action=AuditAction.UPDATE,
            entity_id=role.id,
            entity_display=f"{user.username} → {data.role.value}",
            before_data=before,
            after_data={"role": data.role.value},
        )
        return role

    async def remove_role(
        self, user_id: uuid.UUID, company_id: uuid.UUID, ctx: AuditContext
    ) -> None:
        user = await self.repo.get_by_id_or_raise(user_id, "User")
        role = await self.role_repo.get_role(user_id, company_id)
        if role is None:
            raise NotFoundError("UserCompanyRole", f"{user_id}/{company_id}")

        await self.role_repo.delete(role)
        await self.audit.log(
            ctx=ctx,
            entity_type="user_role",
            action=AuditAction.DELETE,
            entity_id=role.id,
            entity_display=f"{user.username} removed from company {company_id}",
            before_data={"role": role.role.value},
        )
