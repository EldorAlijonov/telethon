"""observability abuse and delivery tables

Revision ID: 0002_observability
Revises: 0001_initial_schema
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_observability"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    delivery_status = postgresql.ENUM("pending", "delivered", "failed", "dead_letter", name="deliverystatus")
    suspicious_kind = postgresql.ENUM("otp_bruteforce", "callback_abuse", "flood", "duplicate_signal", name="suspiciousactivitykind")
    delivery_status.create(op.get_bind(), checkfirst=True)
    suspicious_kind.create(op.get_bind(), checkfirst=True)
    delivery_status = postgresql.ENUM("pending", "delivered", "failed", "dead_letter", name="deliverystatus", create_type=False)
    suspicious_kind = postgresql.ENUM("otp_bruteforce", "callback_abuse", "flood", "duplicate_signal", name="suspiciousactivitykind", create_type=False)

    op.create_table(
        "signal_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signal_id", sa.Integer(), sa.ForeignKey("signals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_tg_id", sa.BigInteger(), nullable=False),
        sa.Column("status", delivery_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("signal_id", "recipient_tg_id", name="uq_signal_delivery_recipient"),
    )
    op.create_index("ix_signal_deliveries_signal_id", "signal_deliveries", ["signal_id"])
    op.create_index("ix_signal_deliveries_recipient_tg_id", "signal_deliveries", ["recipient_tg_id"])
    op.create_index("ix_signal_deliveries_status", "signal_deliveries", ["status"])
    op.create_index("ix_signal_deliveries_status_created", "signal_deliveries", ["status", "created_at"])

    op.create_table(
        "rate_limits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("window_key", sa.String(length=64), nullable=False),
        sa.Column("counter", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("scope", "subject", "window_key", name="uq_rate_limit_window"),
    )
    op.create_index("ix_rate_limits_scope", "rate_limits", ["scope"])
    op.create_index("ix_rate_limits_subject", "rate_limits", ["subject"])
    op.create_index("ix_rate_limits_window_key", "rate_limits", ["window_key"])
    op.create_index("ix_rate_limits_expires_at", "rate_limits", ["expires_at"])

    op.create_table(
        "suspicious_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_id", sa.BigInteger()),
        sa.Column("kind", suspicious_kind, nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_suspicious_activities_tg_id", "suspicious_activities", ["tg_id"])
    op.create_index("ix_suspicious_activities_kind", "suspicious_activities", ["kind"])
    op.create_index("ix_suspicious_activities_severity", "suspicious_activities", ["severity"])


def downgrade() -> None:
    op.drop_table("suspicious_activities")
    op.drop_table("rate_limits")
    op.drop_table("signal_deliveries")
    postgresql.ENUM(name="suspiciousactivitykind").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="deliverystatus").drop(op.get_bind(), checkfirst=True)
