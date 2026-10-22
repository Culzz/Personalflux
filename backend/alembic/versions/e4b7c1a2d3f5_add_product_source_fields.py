"""add product source fields (brand, stock, currency, external_url)

Revision ID: e4b7c1a2d3f5
Revises: bd340f3542e8
Create Date: 2026-10-17 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4b7c1a2d3f5'
down_revision: Union[str, Sequence[str], None] = 'bd340f3542e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the optional columns a live product API can populate."""
    op.add_column('products', sa.Column('brand', sa.String(length=120), nullable=True))
    op.add_column('products', sa.Column('stock', sa.Integer(), nullable=True))
    op.add_column('products', sa.Column('currency', sa.String(length=3), nullable=True))
    op.add_column('products', sa.Column('external_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('products', 'external_url')
    op.drop_column('products', 'currency')
    op.drop_column('products', 'stock')
    op.drop_column('products', 'brand')
