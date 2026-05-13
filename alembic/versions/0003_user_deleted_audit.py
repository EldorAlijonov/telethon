"""add user deleted audit action

Revision ID: 0003_user_deleted
Revises: 0002_observability
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op

revision = "0003_user_deleted"
down_revision = "0002_observability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'user_deleted'")


def downgrade() -> None:
    # PostgreSQL enum qiymatini xavfsiz olib tashlash alohida type recreate talab qiladi.
    pass
