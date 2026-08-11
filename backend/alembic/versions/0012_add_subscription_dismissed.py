"""add dismissed_by_user to subscriptions

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-10

Detection re-activates any subscription whose merchant still matches the
recurring pattern on every run, so a plain is_active=False doesn't stick if
the user says "this isn't really a subscription" — the next sync/nightly run
flips it back on. This flag makes that dismissal permanent: detection skips
a merchant entirely once the user has dismissed it.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("dismissed_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "dismissed_by_user")
