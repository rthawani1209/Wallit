"""add is_demo and demo_chat_count to users

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-27

The recruiter demo hands every visitor a throwaway user seeded with sample
data. is_demo marks those rows so they can be kept away from Plaid, cleaned
up after a day, and given a capped number of assistant messages
(demo_chat_count), since every message is a paid Claude call.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("demo_chat_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_users_is_demo_created_at", "users", ["is_demo", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_users_is_demo_created_at", table_name="users")
    op.drop_column("users", "demo_chat_count")
    op.drop_column("users", "is_demo")
