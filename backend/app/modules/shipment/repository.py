from datetime import date
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.shipment.models import Shipment, ShipmentCancellation, ShipmentLine
from app.shared.base_repository import BaseRepository
from app.shared.enums import ShipmentStatus


class ShipmentRepository(BaseRepository[Shipment]):
    model = Shipment

    async def get_with_lines(
        self, shipment_id: uuid.UUID, company_id: uuid.UUID
    ) -> Shipment | None:
        result = await self.session.execute(
            select(Shipment)
            .options(selectinload(Shipment.lines))
            .where(Shipment.id == shipment_id, Shipment.company_id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, company_id: uuid.UUID, number: str) -> Shipment | None:
        result = await self.session.execute(
            select(Shipment).where(
                Shipment.company_id == company_id,
                Shipment.shipment_number == number,
            )
        )
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        company_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        buyer_id: uuid.UUID | None = None,
        status: ShipmentStatus | None = None,
        lot_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Shipment], int]:
        conditions = [Shipment.company_id == company_id]
        if warehouse_id is not None:
            conditions.append(Shipment.warehouse_id == warehouse_id)
        if buyer_id is not None:
            conditions.append(Shipment.buyer_id == buyer_id)
        if status is not None:
            conditions.append(Shipment.status == status)
        if date_from is not None:
            conditions.append(Shipment.shipment_date >= date_from)
        if date_to is not None:
            conditions.append(Shipment.shipment_date <= date_to)
        if lot_id is not None:
            from sqlalchemy import exists
            conditions.append(
                exists().where(
                    ShipmentLine.shipment_id == Shipment.id,
                    ShipmentLine.lot_id == lot_id,
                )
            )

        total = await self.count(*conditions)
        result = await self.session.execute(
            select(Shipment)
            .options(selectinload(Shipment.lines))
            .where(*conditions)
            .order_by(Shipment.shipment_date.desc(), Shipment.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_line(self, line_id: uuid.UUID) -> ShipmentLine | None:
        result = await self.session.execute(
            select(ShipmentLine).where(ShipmentLine.id == line_id)
        )
        return result.scalar_one_or_none()

    async def save_cancellation(
        self,
        cancellation: ShipmentCancellation,
    ) -> ShipmentCancellation:
        self.session.add(cancellation)
        await self.session.flush()
        await self.session.refresh(cancellation)
        return cancellation
