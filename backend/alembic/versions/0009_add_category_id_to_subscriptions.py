"""add category_id to subscriptions

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('subscriptions', sa.Column('category_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'fk_subscriptions_category_id', 'subscriptions', 'categories', ['category_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_subscriptions_category_id', 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'category_id')
