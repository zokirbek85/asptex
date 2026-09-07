import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.base_model import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, id: uuid.UUID, resource_name: str | None = None) -> ModelT:
        from app.core.exceptions import NotFoundError

        obj = await self.get_by_id(id)
        if obj is None:
            raise NotFoundError(resource_name or self.model.__name__, id)
        return obj

    async def get_scoped(self, id: uuid.UUID, company_id: uuid.UUID) -> ModelT | None:
        """Like get_by_id, but also requires the row's company_id to match.

        Used to close multi-tenant IDOR gaps: an id that exists but belongs
        to a different company is treated as not found.
        """
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id,  # type: ignore[attr-defined]
                self.model.company_id == company_id,  # type: ignore[attr-defined]
            )
        )
        return result.scalar_one_or_none()

    async def get_scoped_or_raise(
        self, id: uuid.UUID, company_id: uuid.UUID, resource_name: str | None = None
    ) -> ModelT:
        from app.core.exceptions import NotFoundError

        obj = await self.get_scoped(id, company_id)
        if obj is None:
            raise NotFoundError(resource_name or self.model.__name__, id)
        return obj

    async def list_all(self) -> list[ModelT]:
        result = await self.session.execute(select(self.model))
        return list(result.scalars().all())

    async def count(self, *where_clauses) -> int:
        stmt = select(func.count()).select_from(self.model)
        if where_clauses:
            stmt = stmt.where(*where_clauses)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def save(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
