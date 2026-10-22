"""named lists a customer curates

A list belongs to one customer and holds references to products. Deleting a list
takes its entries with it and leaves the catalog alone, so RESTRICT on the
product side is deliberate.

Revision ID: e9a4c2b8f1d3
Revises: d6f2a8c1e5b3
Create Date: 2026-10-19 11:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e9a4c2b8f1d3'
down_revision: Union[str, Sequence[str], None] = 'd6f2a8c1e5b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the collections and collection_items tables."""
    op.create_table(
        'collections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_collections_user_name'),
    )
    op.create_index('ix_collections_user_id', 'collections', ['user_id'])

    op.create_table(
        'collection_items',
        sa.Column('collection_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('collection_id', 'product_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('collection_items')
    op.drop_index('ix_collections_user_id', table_name='collections')
    op.drop_table('collections')
