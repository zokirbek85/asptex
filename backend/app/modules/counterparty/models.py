import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.shared.enums import CounterpartyType

if TYPE_CHECKING:
    from app.modules.contract.models import Contract


class Counterparty(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "counterparties"
    __table_args__ = (
        UniqueConstraint("company_id", "tax_id", name="uq_counterparty_company_tax"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    counterparty_type: Mapped[CounterpartyType] = mapped_column(
        nullable=False, default=CounterpartyType.BUYER
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Relationships
    contacts: Mapped[list["CounterpartyContact"]] = relationship(
        "CounterpartyContact", back_populates="counterparty", cascade="all, delete-orphan"
    )
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract", back_populates="counterparty"
    )
    merged_into: Mapped["Counterparty | None"] = relationship(
        "Counterparty", remote_side="Counterparty.id"
    )


class CounterpartyContact(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "counterparty_contacts"

    counterparty_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("counterparties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PHONE, EMAIL, etc.
    contact_value: Mapped[str] = mapped_column(String(255), nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationship
    counterparty: Mapped["Counterparty"] = relationship("Counterparty", back_populates="contacts")
