"""add session-scoped preferences and liked brands

Preferences can now belong to an anonymous session, so the first-visit
onboarding works before anyone registers.

Revision ID: f7a2b9c4d1e6
Revises: e4b7c1a2d3f5
Create Date: 2026-10-17 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7a2b9c4d1e6'
down_revision: Union[str, Sequence[str], None] = 'e4b7c1a2d3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_TYPES = "'liked_categories', 'blocked_categories', 'price_range'"
_NEW_TYPES = "'liked_categories', 'blocked_categories', 'liked_brands', 'price_range'"


def upgrade() -> None:
    """Preferences gain a session owner and a brand dimension."""
    op.add_column('preferences', sa.Column('session_id', sa.String(length=64), nullable=True))
    op.alter_column('preferences', 'user_id', existing_type=sa.Uuid(), nullable=True)
    op.drop_constraint('uq_preferences_user_type', 'preferences', type_='unique')
    op.create_index('uq_preferences_user_type', 'preferences', ['user_id', 'preference_type'],
                    unique=True, postgresql_where=sa.text('user_id IS NOT NULL'))
    op.create_index('uq_preferences_session_type', 'preferences', ['session_id', 'preference_type'],
                    unique=True, postgresql_where=sa.text('session_id IS NOT NULL'))
    op.create_check_constraint('ck_preferences_has_actor', 'preferences',
                               'user_id IS NOT NULL OR session_id IS NOT NULL')
    op.create_check_constraint('ck_preferences_one_actor', 'preferences',
                               'user_id IS NULL OR session_id IS NULL')
    op.drop_constraint('ck_preferences_type', 'preferences', type_='check')
    op.create_check_constraint('ck_preferences_type', 'preferences',
                               f"preference_type IN ({_NEW_TYPES})")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_preferences_type', 'preferences', type_='check')
    op.create_check_constraint('ck_preferences_type', 'preferences',
                               f"preference_type IN ({_OLD_TYPES})")
    op.drop_constraint('ck_preferences_one_actor', 'preferences', type_='check')
    op.drop_constraint('ck_preferences_has_actor', 'preferences', type_='check')
    op.drop_index('uq_preferences_session_type', table_name='preferences')
    op.drop_index('uq_preferences_user_type', table_name='preferences')
    # Session-only rows cannot survive a NOT NULL user_id, so they go first.
    op.execute("DELETE FROM preferences WHERE user_id IS NULL")
    op.create_unique_constraint('uq_preferences_user_type', 'preferences',
                                ['user_id', 'preference_type'])
    op.alter_column('preferences', 'user_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_column('preferences', 'session_id')
