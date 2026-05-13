"""initial production schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_status = postgresql.ENUM("pending", "approved", "blocked", "expired", "rejected", name="userstatus")
    broadcast_status = postgresql.ENUM("pending", "running", "finished", "failed", name="broadcaststatus")
    audit_action = postgresql.ENUM(
        "user_registered",
        "user_approved",
        "user_rejected",
        "user_blocked",
        "session_connected",
        "session_revoked",
        "monitoring_started",
        "monitoring_stopped",
        "signal_sent",
        "broadcast_created",
        name="auditaction",
    )
    user_status.create(op.get_bind(), checkfirst=True)
    broadcast_status.create(op.get_bind(), checkfirst=True)
    audit_action.create(op.get_bind(), checkfirst=True)
    user_status = postgresql.ENUM("pending", "approved", "blocked", "expired", "rejected", name="userstatus", create_type=False)
    broadcast_status = postgresql.ENUM("pending", "running", "finished", "failed", name="broadcaststatus", create_type=False)
    audit_action = postgresql.ENUM(
        "user_registered",
        "user_approved",
        "user_rejected",
        "user_blocked",
        "session_connected",
        "session_revoked",
        "monitoring_started",
        "monitoring_stopped",
        "signal_sent",
        "broadcast_created",
        name="auditaction",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tg_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("username", sa.String(length=128)),
        sa.Column("phone", sa.String(length=32)),
        sa.Column("status", user_status, nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tg_id"),
    )
    op.create_index("ix_users_tg_id", "users", ["tg_id"])
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_expires_at", "users", ["expires_at"])
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table("approvals", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("admin_tg_id", sa.BigInteger()), sa.Column("decision", sa.String(length=32), nullable=False), sa.Column("reason", sa.Text()), sa.Column("access_days", sa.Integer()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_approvals_user_id", "approvals", ["user_id"])
    op.create_table("subscriptions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("source", sa.String(length=64), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_expires_at", "subscriptions", ["expires_at"])
    op.create_index("ix_subscriptions_is_active", "subscriptions", ["is_active"])
    op.create_table("keywords", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("keyword", sa.String(length=128), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("user_id", "keyword", name="uq_keywords_user_keyword"))
    op.create_index("ix_keywords_user_id", "keywords", ["user_id"])
    op.create_index("ix_keywords_is_active", "keywords", ["is_active"])
    op.create_table("monitored_chats", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("chat_id", sa.BigInteger(), nullable=False), sa.Column("title", sa.String(length=255)), sa.Column("username", sa.String(length=128)), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("user_id", "chat_id", name="uq_monitored_chats_user_chat"))
    op.create_index("ix_monitored_chats_user_id", "monitored_chats", ["user_id"])
    op.create_index("ix_monitored_chats_chat_id", "monitored_chats", ["chat_id"])
    op.create_index("ix_monitored_chats_is_active", "monitored_chats", ["is_active"])
    op.create_table("telegram_sessions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True), sa.Column("phone", sa.String(length=32), nullable=False), sa.Column("encrypted_session", sa.Text(), nullable=False), sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("signals", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE")), sa.Column("chat_id", sa.BigInteger(), nullable=False), sa.Column("message_id", sa.BigInteger(), nullable=False), sa.Column("keyword", sa.String(length=128), nullable=False), sa.Column("matched_text", sa.Text(), nullable=False), sa.Column("source_chat", sa.String(length=255)), sa.Column("sender_info", sa.String(length=255)), sa.Column("message_link", sa.Text()), sa.Column("message_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("user_id", "chat_id", "message_id", "keyword", name="uq_signal_dedupe"))
    op.create_index("ix_signals_user_created", "signals", ["user_id", "created_at"])
    op.create_index("ix_signals_chat_id", "signals", ["chat_id"])
    op.create_index("ix_signals_keyword", "signals", ["keyword"])
    op.create_table("broadcast_jobs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("admin_tg_id", sa.BigInteger(), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("status", broadcast_status, nullable=False), sa.Column("total_count", sa.Integer(), nullable=False), sa.Column("sent_count", sa.Integer(), nullable=False), sa.Column("failed_count", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_broadcast_jobs_admin_tg_id", "broadcast_jobs", ["admin_tg_id"])
    op.create_index("ix_broadcast_jobs_status", "broadcast_jobs", ["status"])
    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor_tg_id", sa.BigInteger()), sa.Column("target_tg_id", sa.BigInteger()), sa.Column("action", audit_action, nullable=False), sa.Column("details", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_audit_logs_actor_tg_id", "audit_logs", ["actor_tg_id"])
    op.create_index("ix_audit_logs_target_tg_id", "audit_logs", ["target_tg_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_table("settings", sa.Column("key", sa.String(length=128), primary_key=True), sa.Column("value", postgresql.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    for table in ["settings", "audit_logs", "broadcast_jobs", "signals", "telegram_sessions", "monitored_chats", "keywords", "subscriptions", "approvals", "users"]:
        op.drop_table(table)
    for enum_name in ["auditaction", "broadcaststatus", "userstatus"]:
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
