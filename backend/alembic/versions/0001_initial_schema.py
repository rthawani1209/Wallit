"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("plaid_access_token", sa.Text(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "linked_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_user_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_provider_identity"),
    )
    op.create_index("ix_linked_identities_user_id", "linked_identities", ["user_id"])

    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plaid_account_id", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("current_balance", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])

    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
    )

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("target_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_plans_user_id", "plans", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("plaid_transaction_id", sa.String(), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("merchant_name", sa.String(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=True),
        sa.Column("is_subscription", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_date", "transactions", ["date"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_plan_id", "transactions", ["plan_id"])
    op.create_index("ix_transactions_account_date", "transactions", ["account_id", "date"])

    op.create_table(
        "plan_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("plans.id"), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("estimated_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_amount", sa.Numeric(12, 2), nullable=True),
    )
    op.create_index("ix_plan_line_items_plan_id", "plan_line_items", ["plan_id"])

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("transaction_pattern_id", sa.String(), nullable=True),
        sa.Column("merchant_name", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("billing_interval", sa.String(), nullable=False),
        sa.Column("next_estimated_date", sa.Date(), nullable=True),
        sa.Column("cheaper_alternative", sa.Text(), nullable=True),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])

    op.create_table(
        "bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_subscription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("subscriptions.id"), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
    )
    op.create_index("ix_bills_user_id", "bills", ["user_id"])
    op.create_index("ix_bills_due_date", "bills", ["due_date"])


def downgrade() -> None:
    op.drop_table("bills")
    op.drop_table("subscriptions")
    op.drop_table("plan_line_items")
    op.drop_table("transactions")
    op.drop_table("plans")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.drop_table("linked_identities")
    op.drop_table("users")
