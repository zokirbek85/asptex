import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import UserRole

if TYPE_CHECKING:
    from app.modules.auth.models import User
    from app.modules.company.models import Company
    from app.modules.warehouse.models import Warehouse


class UserCompanyRole(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_company_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    role: Mapped[UserRole] = mapped_column(nullable=False)
    warehouse_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="company_roles")
    company: Mapped["Company"] = relationship("Company", back_populates="user_roles")
    warehouse: Mapped["Warehouse | None"] = relationship("Warehouse")
