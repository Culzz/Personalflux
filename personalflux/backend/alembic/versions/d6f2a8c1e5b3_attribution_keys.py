"""attribution keys for impressions and events

An impression now carries a stable key (`request_id:product_id`) and a click can
name the same key, so a click is attributable to the recommendation request and
model version that produced it instead of only being countable. Existing rows are
backfilled from data already stored.

Revision ID: d6f2a8c1e5b3
Revises: c4e8f1a2b7d9
Create Date: 2026-10-17 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd6f2a8c1e5b3'
down_revision: Union[str, Sequence[str], None] = 'c4e8f1a2b7d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add impression keys and event attribution columns."""
    op.add_column('recommendation_impressions',
                  sa.Column('impression_id', sa.String(length=120), nullable=True))
    op.execute("UPDATE recommendation_impressions "
               "SET impression_id = left(request_id || ':' || product_id::text, 120) "
               "WHERE impression_id IS NULL")
    op.alter_column('recommendation_impressions', 'impression_id',
                    existing_type=sa.String(length=120), nullable=False)
    op.create_index('ix_recommendation_impressions_impression_id', 'recommendation_impressions',
                    ['impression_id'], unique=True)
    op.create_index('ix_impressions_product_time', 'recommendation_impressions',
                    ['product_id', 'created_at'])

    op.add_column('interactions', sa.Column('request_id', sa.String(length=64), nullable=True))
    op.add_column('interactions', sa.Column('impression_id', sa.String(length=120), nullable=True))
    op.add_column('interactions', sa.Column('position', sa.Integer(), nullable=True))
    op.add_column('interactions', sa.Column('model_version', sa.String(length=100), nullable=True))
    op.create_index('ix_interactions_impression', 'interactions', ['impression_id'])

    # Backfill from the JSON context older events already carry.
    op.execute("""
        UPDATE interactions SET
            request_id    = left(NULLIF(context->>'request_id', ''), 64),
            model_version = left(NULLIF(context->>'model_version', ''), 100),
            position      = CASE WHEN (context->>'position') ~ '^[0-9]+$'
                                 THEN (context->>'position')::int END,
            impression_id = CASE
                WHEN NULLIF(context->>'request_id', '') IS NOT NULL AND product_id IS NOT NULL
                THEN left(NULLIF(context->>'request_id', '') || ':' || product_id::text, 120)
            END
        WHERE context IS NOT NULL
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_interactions_impression', table_name='interactions')
    op.drop_column('interactions', 'model_version')
    op.drop_column('interactions', 'position')
    op.drop_column('interactions', 'impression_id')
    op.drop_column('interactions', 'request_id')
    op.drop_index('ix_impressions_product_time', table_name='recommendation_impressions')
    op.drop_index('ix_recommendation_impressions_impression_id',
                  table_name='recommendation_impressions')
    op.drop_column('recommendation_impressions', 'impression_id')
