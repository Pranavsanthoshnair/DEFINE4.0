"""Add retry, suppression, adaptive scheduling, and erasure tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7a3b2c1d4e5f"
down_revision = "e90e4907f2e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_log", sa.Column("prev_hash", sa.String(64), nullable=True))
    op.add_column("audit_log", sa.Column("row_hash", sa.String(64), nullable=True))
    op.create_table(
        "slot_stats",
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("segment", sa.Text(), nullable=False),
        sa.Column("slot_idx", sa.Integer(), nullable=False),
        sa.Column("successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("scope", "segment", "slot_idx"),
    )
    op.create_table(
        "contact_slot_stats",
        sa.Column("campaign_contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slot_idx", sa.Integer(), nullable=False),
        sa.Column("successes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failures", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["campaign_contact_id"], ["campaign_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("campaign_contact_id", "slot_idx"),
    )
    op.create_table(
        "retry_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("campaign_contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_mode", sa.Text(), nullable=False),
        sa.Column("slot_idx", sa.Integer(), nullable=True),
        sa.Column("sampled_theta", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_contact_id"], ["campaign_contacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "suppression_layers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("layer_no", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("n_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("k", sa.Integer(), nullable=False),
        sa.Column("m_bits", sa.Integer(), nullable=False),
        sa.Column("bits", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("layer_no"),
    )
    op.create_table(
        "erasure_ledger",
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("contact_id"),
    )


def downgrade() -> None:
    op.drop_table("erasure_ledger")
    op.drop_table("suppression_layers")
    op.drop_table("retry_decisions")
    op.drop_table("contact_slot_stats")
    op.drop_table("slot_stats")
    op.drop_column("audit_log", "row_hash")
    op.drop_column("audit_log", "prev_hash")
