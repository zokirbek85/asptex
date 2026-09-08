import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import BuntStatus

if TYPE_CHECKING:
    from app.modules.lot.models import Lot


class GinningBunt(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A physical raw-cotton storage aggregation ("Bunt") that may contain cotton
    from multiple farmers/receivings. Satellite table extending a generic Lot,
    exactly mirroring how TollingLot extends Lot for the tolling business.
    Farmer composition is NOT stored here — it is derived from CottonReceiving
    rows (bunt_id + farmer_id + net_weight_kg), each of which is already a
    per-event record.
    """
    __tablename__ = "ginning_bunts"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id"), nullable=False, unique=True
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False, index=True
    )
    status: Mapped[BuntStatus] = mapped_column(nullable=False, default=BuntStatus.OPEN)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    close_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    lot: Mapped["Lot"] = relationship("Lot", lazy="joined")
