"""revise categories to a leaner top-level taxonomy

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-08

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Categories kept, just renamed (id stable, existing transactions stay correctly categorized)
RENAMES = {
    "Groceries": "Food",
    "Healthcare": "Health",
    "Other": "Fees/Other",
}

# Categories merged into an existing one — their transactions get reassigned before the
# now-empty category row is deleted.
MERGES = {
    "Dining": "Food",  # "Food" here refers to the post-rename name (was Groceries)
    "Travel": "Transportation",
}

NEW_CATEGORIES = ["Debt", "Savings", "Giving"]

categories_table = sa.table(
    "categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String()),
)
transactions_table = sa.table(
    "transactions",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("category_id", postgresql.UUID(as_uuid=True)),
)


def upgrade() -> None:
    conn = op.get_bind()

    for old_name, new_name in RENAMES.items():
        conn.execute(
            categories_table.update()
            .where(categories_table.c.name == old_name)
            .values(name=new_name)
        )

    for old_name, target_name in MERGES.items():
        old_id = conn.execute(
            sa.select(categories_table.c.id).where(categories_table.c.name == old_name)
        ).scalar()
        target_id = conn.execute(
            sa.select(categories_table.c.id).where(categories_table.c.name == target_name)
        ).scalar()
        if old_id and target_id:
            conn.execute(
                transactions_table.update()
                .where(transactions_table.c.category_id == old_id)
                .values(category_id=target_id)
            )
            conn.execute(categories_table.delete().where(categories_table.c.id == old_id))

    op.bulk_insert(
        categories_table,
        [{"id": uuid.uuid4(), "name": name} for name in NEW_CATEGORIES],
    )


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        categories_table.delete().where(categories_table.c.name.in_(NEW_CATEGORIES))
    )

    # Merged categories (Dining, Travel) can't be reconstructed with their original
    # transaction assignments — recreate the rows only, transactions stay on the merge target.
    op.bulk_insert(
        categories_table,
        [{"id": uuid.uuid4(), "name": name} for name in MERGES.keys()],
    )

    for old_name, new_name in RENAMES.items():
        conn.execute(
            categories_table.update()
            .where(categories_table.c.name == new_name)
            .values(name=old_name)
        )
