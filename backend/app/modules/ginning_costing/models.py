import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, UUIDPrimaryKeyMixin
from app.shared.enums import GinningCostType


class GinningProductionCost(Base, UUIDPrimaryKeyMixin):
    """
    Manually entered production cost lines (electricity, gas, labor, etc).
    RAW_MATERIAL cost is NEVER stored here — it is always computed live from
    the order's consumed bunts' weighted-average farmer price, so it can never
    drift out of sync with the farmer ledger.
    """
    __tablename__ = "ginning_production_costs"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_gpc_amount_positive"),
        CheckConstraint("cost_type != 'RAW_MATERIAL'", name="chk_gpc_no_raw_material"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    production_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ginning_production_orders.id"), nullable=False, index=True
    )
    cost_type: Mapped[GinningCostType] = mapped_column(nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UZS")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
