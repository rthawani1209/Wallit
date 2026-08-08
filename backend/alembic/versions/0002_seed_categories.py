"""seed default categories

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-08

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIES = [
    "Groceries",
    "Housing",
    "Transportation",
    "Dining",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Travel",
    "Subscriptions",
    "Income",
    "Other",
]

categories_table = sa.table(
    "categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String()),
)


def upgrade() -> None:
    op.bulk_insert(
        categories_table,
        [{"id": uuid.uuid4(), "name": name} for name in CATEGORIES],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        categories_table.delete().where(categories_table.c.name.in_(CATEGORIES))
    )
