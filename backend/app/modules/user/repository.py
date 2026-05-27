import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.auth.models import User
from app.modules.user.models import UserCompanyRole
from app.shared.base_repository import BaseRepository


class UserManagementRepository(BaseRepository[User]):
    model = User

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_with_roles(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.company_roles)
                .selectinload(UserCompanyRole.company),
                selectinload(User.company_roles)
                .selectinload(UserCompanyRole.warehouse),
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        active_only: bool = False,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        where = []
        if active_only:
            where.append(User.is_active.is_(True))
        if search:
            pattern = f"%{search}%"
            from sqlalchemy import or_
            where.append(
                or_(
                    User.username.ilike(pattern),
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        total = await self.count(*where)
        result = await self.session.execute(
            select(User)
            .where(*where)
            .options(
                selectinload(User.company_roles)
                .selectinload(UserCompanyRole.company),
                selectinload(User.company_roles)
                .selectinload(UserCompanyRole.warehouse),
            )
            .order_by(User.username)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total


class UserCompanyRoleRepository(BaseRepository[UserCompanyRole]):
    model = UserCompanyRole

    async def get_role(
        self, user_id: uuid.UUID, company_id: uuid.UUID
    ) -> UserCompanyRole | None:
        result = await self.session.execute(
            select(UserCompanyRole).where(
                UserCompanyRole.user_id == user_id,
                UserCompanyRole.company_id == company_id,
            )
        )
        return result.scalar_one_or_none()
