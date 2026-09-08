"""ginning phase 2: bunts, cotton receiving, price list, farmer ledger

Revision ID: 20260908_ginning_p2
Revises: 20260908_ginning_p1
Create Date: 2026-09-08

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM, UUID

revision = "20260908_ginning_p2"
down_revision = "20260908_ginning_p1"
branch_labels = None
depends_on = None


def upgrade():
    bunt_status = ENUM("OPEN", "CLOSED", name="buntstatus", create_type=True)
    bunt_status.create(op.get_bind(), checkfirst=True)

    receiving_status = ENUM("DRAFT", "POSTED", "CANCELLED", name="cottonreceivingstatus", create_type=True)
    receiving_status.create(op.get_bind(), checkfirst=True)

    ledger_entry_type = ENUM(
        "RECEIVABLE_COTTON", "ADVANCE_PAYMENT", "PAYMENT", "DEDUCTION", "ADJUSTMENT",
        name="farmerledgerentrytype", create_type=True,
    )
    ledger_entry_type.create(op.get_bind(), checkfirst=True)

    # ── ginning_bunts ──────────────────────────────────────────────────────
    op.create_table(
        "ginning_bunts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("lot_id", UUID(as_uuid=True), sa.ForeignKey("lots.id"), nullable=False, unique=True),
        sa.Column("warehouse_id", UUID(as_uuid=True), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("status", ENUM("OPEN", "CLOSED", name="buntstatus", create_type=False), nullable=False, server_default="OPEN"),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("close_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ginning_bunts_company_id", "ginning_bunts", ["company_id"])
    op.create_index("ix_ginning_bunts_warehouse_id", "ginning_bunts", ["warehouse_id"])

    # ── cotton_receiving_number_sequences ──────────────────────────────────
    op.create_table(
        "cotton_receiving_number_sequences",
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), primary_key=True),
        sa.Column("year", sa.SmallInteger, primary_key=True),
        sa.Column("last_sequence", sa.SmallInteger, nullable=False, server_default="0"),
    )

    # ── cotton_price_list ───────────────────────────────────────────────────
    op.create_table(
        "cotton_price_list",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("variety", sa.String(50), nullable=True),
        sa.Column("sort", sa.String(20), nullable=True),
        sa.Column("quality_class", sa.String(20), nullable=True),
        sa.Column("price_per_kg", sa.Numeric(18, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_cotton_price_list_company_id", "cotton_price_list", ["company_id"])

    # ── cotton_receiving ────────────────────────────────────────────────────
    op.create_table(
        "cotton_receiving",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("bunt_id", UUID(as_uuid=True), sa.ForeignKey("ginning_bunts.id"), nullable=False),
        sa.Column("farmer_id", UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=True),
        sa.Column("receiving_number", sa.String(30), nullable=False),
        sa.Column("receiving_date", sa.Date, nullable=False),
        sa.Column("vehicle_number", sa.String(30), nullable=True),
        sa.Column("driver_name", sa.String(100), nullable=True),
        sa.Column("gross_weight_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("tare_weight_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("net_weight_kg", sa.Numeric(15, 3), nullable=False),
        sa.Column("moisture_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("contamination_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("grade", sa.String(20), nullable=True),
        sa.Column("variety", sa.String(50), nullable=True),
        sa.Column("sort", sa.String(20), nullable=True),
        sa.Column("quality_class", sa.String(20), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=True),
        sa.Column("price_source", sa.String(20), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("status", ENUM("DRAFT", "POSTED", "CANCELLED", name="cottonreceivingstatus", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("transaction_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ledger_entry_id", UUID(as_uuid=True), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("posted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text, nullable=True),
        sa.Column("farmer_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("company_id", "receiving_number", name="uq_cotton_receiving_company_number"),
        sa.CheckConstraint("gross_weight_kg > tare_weight_kg", name="chk_cr_gross_gt_tare"),
        sa.CheckConstraint("net_weight_kg > 0", name="chk_cr_net_positive"),
    )
    op.create_index("ix_cotton_receiving_company_id", "cotton_receiving", ["company_id"])
    op.create_index("ix_cotton_receiving_bunt_id", "cotton_receiving", ["bunt_id"])
    op.create_index("ix_cotton_receiving_farmer_id", "cotton_receiving", ["farmer_id"])
    op.create_index("ix_cotton_receiving_receiving_date", "cotton_receiving", ["receiving_date"])

    # ── farmer_ledger_entries ───────────────────────────────────────────────
    op.create_table(
        "farmer_ledger_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("farmer_id", UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=False),
        sa.Column("entry_type", ENUM(
            "RECEIVABLE_COTTON", "ADVANCE_PAYMENT", "PAYMENT", "DEDUCTION", "ADJUSTMENT",
            name="farmerledgerentrytype", create_type=False,
        ), nullable=False),
        sa.Column("direction", sa.SmallInteger, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="UZS"),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("entry_date", sa.Date, nullable=False),
        sa.Column("posted_by", UUID(as_uuid=True), nullable=False),
        sa.Column("farmer_name", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("direction IN (1, -1)", name="chk_fle_direction"),
        sa.CheckConstraint("amount > 0", name="chk_fle_amount_positive"),
    )
    op.create_index("idx_fle_balance_key", "farmer_ledger_entries", ["company_id", "farmer_id"])
    op.create_index("idx_fle_reference", "farmer_ledger_entries", ["reference_type", "reference_id"])
    op.create_index("ix_farmer_ledger_entries_entry_date", "farmer_ledger_entries", ["entry_date"])


def downgrade():
    op.drop_table("farmer_ledger_entries")
    op.drop_table("cotton_receiving")
    op.drop_table("cotton_price_list")
    op.drop_table("cotton_receiving_number_sequences")
    op.drop_table("ginning_bunts")
    ENUM(name="farmerledgerentrytype").drop(op.get_bind(), checkfirst=True)
    ENUM(name="cottonreceivingstatus").drop(op.get_bind(), checkfirst=True)
    ENUM(name="buntstatus").drop(op.get_bind(), checkfirst=True)
