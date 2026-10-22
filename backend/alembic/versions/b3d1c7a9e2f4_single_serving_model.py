"""one serving model per database

Promotion writes a single "serving" row. A partial unique index makes that a
database rule rather than a convention, so two concurrent promotions cannot
leave the system with two active models.

Revision ID: b3d1c7a9e2f4
Revises: f7a2b9c4d1e6
Create Date: 2026-10-17 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b3d1c7a9e2f4'
down_revision: Union[str, Sequence[str], None] = 'f7a2b9c4d1e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """At most one row may be 'serving'."""
    # A database written before this rule could hold several. Keep the most
    # recently promoted one and retire the rest.
    op.execute("""
        UPDATE model_versions SET status = 'retired'
        WHERE status = 'serving'
          AND id <> (
              SELECT id FROM model_versions
              WHERE status = 'serving'
              ORDER BY promoted_at DESC NULLS LAST, created_at DESC
              LIMIT 1
          )
    """)
    op.create_index('uq_model_versions_one_serving', 'model_versions', ['status'],
                    unique=True, postgresql_where=sa.text("status = 'serving'"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_model_versions_one_serving', table_name='model_versions')
