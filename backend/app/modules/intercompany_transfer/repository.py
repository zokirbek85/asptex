import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.modules.intercompany_transfer.models import IntercompanyTransfer
from app.shared.base_repository import BaseRepository
from app.shared.enums import IntercompanyTransferStatus


class IntercompanyTransferRepository(BaseRepository[IntercompanyTransfer]):
    model = IntercompanyTransfer

    async def get_visible_or_raise(
        self, transfer_id: uuid.UUID, company_id: uuid.UUID
    ) -> IntercompanyTransfer:
        from app.core.exceptions import NotFoundError

        result = await self.session.execute(
            select(IntercompanyTransfer)
            .options(selectinload(IntercompanyTransfer.lines))
            .where(
                IntercompanyTransfer.id == transfer_id,
                or_(
                    IntercompanyTransfer.source_company_id == company_id,
                    IntercompanyTransfer.destination_company_id == company_id,
                ),
            )
        )
        transfer = result.scalar_one_or_none()
        if transfer is None:
            raise NotFoundError("IntercompanyTransfer", transfer_id)
        return transfer

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        page: int,
        page_size: int,
        status: IntercompanyTransferStatus | None = None,
    ) -> tuple[list[IntercompanyTransfer], int]:
        conditions = [
            or_(
                IntercompanyTransfer.source_company_id == company_id,
                IntercompanyTransfer.destination_company_id == company_id,
            )
        ]
        if status is not None:
            conditions.append(IntercompanyTransfer.status == status)

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(IntercompanyTransfer)
            .options(selectinload(IntercompanyTransfer.lines))
            .where(*conditions)
            .order_by(IntercompanyTransfer.transfer_date.desc(), IntercompanyTransfer.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total
