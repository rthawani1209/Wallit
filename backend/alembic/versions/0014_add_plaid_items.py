"""move Plaid tokens into a plaid_items table, one row per linked bank

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-03

users.plaid_access_token held a single token, so linking a second bank
overwrote the first and its accounts stopped syncing. Each linked bank now
gets its own row with its own token and /transactions/sync cursor. Existing
tokens are copied over and the user's accounts are attached to them.

users.plaid_access_token is left in place for now: the old container keeps
serving while this migration runs on deploy, and its User model still maps
that column. A later migration drops it once this release is confirmed.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plaid_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_id", sa.String(), nullable=True, unique=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("institution_name", sa.String(), nullable=True),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_plaid_items_user_id", "plaid_items", ["user_id"])
    op.add_column(
        "accounts",
        sa.Column("plaid_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plaid_items.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_accounts_plaid_item_id", "accounts", ["plaid_item_id"])

    # Copy each existing token into its own item and hang the user's accounts off it.
    op.execute(
        """
        INSERT INTO plaid_items (id, user_id, access_token)
        SELECT gen_random_uuid(), id, plaid_access_token FROM users WHERE plaid_access_token IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE accounts SET plaid_item_id = plaid_items.id
        FROM plaid_items WHERE plaid_items.user_id = accounts.user_id
        """
    )


def downgrade() -> None:
    # users.plaid_access_token was never dropped, so the old code picks up
    # where it left off. Banks linked since the upgrade aren't carried back.
    op.drop_index("ix_accounts_plaid_item_id", table_name="accounts")
    op.drop_column("accounts", "plaid_item_id")
    op.drop_index("ix_plaid_items_user_id", table_name="plaid_items")
    op.drop_table("plaid_items")
