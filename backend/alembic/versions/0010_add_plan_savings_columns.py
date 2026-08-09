"""add monthly_contribution and is_active to plans

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('plans', sa.Column('monthly_contribution', sa.Numeric(12, 2), nullable=True))
    op.add_column(
        'plans', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true())
    )


def downgrade() -> None:
    op.drop_column('plans', 'is_active')
    op.drop_column('plans', 'monthly_contribution')
