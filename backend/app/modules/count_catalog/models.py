import uuid
from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CountCatalog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "count_catalog"
    __table_args__ = (
        UniqueConstraint("company_id", "count_value", name="uq_count_company_value"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    count_value: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. "30/1", "26/1"
    yarn_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    composition: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
