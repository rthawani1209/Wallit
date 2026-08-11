"""add a dedicated Transfer category

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-10

Money moving between the user's own linked accounts was previously mapped to
"Income" (in) or "Fees/Other" (out), which made a transfer look like real
income/spending — a $2,000 transfer showed up as both a $2,000 "gain" and a
$2,000 "loss". Giving transfers their own category lets the cash flow chart
and spend breakdown exclude them entirely, same as Mint/YNAB do.
"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_CATEGORIES = ["Transfer"]

categories_table = sa.table(
    "categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String()),
)


def upgrade() -> None:
    op.bulk_insert(
        categories_table,
        [{"id": uuid.uuid4(), "name": name} for name in NEW_CATEGORIES],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        categories_table.delete().where(categories_table.c.name.in_(NEW_CATEGORIES))
    )
