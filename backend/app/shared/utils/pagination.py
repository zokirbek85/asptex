from fastapi import Query
from pydantic import BaseModel

from app.core.config import settings


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = settings.DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return min(self.page_size, settings.MAX_PAGE_SIZE)


def pagination_params(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
