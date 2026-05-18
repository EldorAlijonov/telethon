"""add signal destination to users

Revision ID: 0004_signal_destination
Revises: 0003_user_deleted
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_signal_destination"
down_revision = "0003_user_deleted"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("signal_destination_chat_id", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("signal_destination_title", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "signal_destination_title")
    op.drop_column("users", "signal_destination_chat_id")
