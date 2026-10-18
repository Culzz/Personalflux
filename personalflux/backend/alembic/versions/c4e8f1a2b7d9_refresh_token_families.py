"""refresh token families and rotation bookkeeping

Rotation already retired the old token; this records which login a token belongs
to so a replayed token can end exactly that family, and keeps the reason and
time of rotation so a short grace window can tell a two-tab race apart from theft.

Revision ID: c4e8f1a2b7d9
Revises: b3d1c7a9e2f4
Create Date: 2026-10-17 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4e8f1a2b7d9'
down_revision: Union[str, Sequence[str], None] = 'b3d1c7a9e2f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a family id, rotation time, and revocation reason to refresh tokens."""
    op.add_column('refresh_tokens', sa.Column('family_id', sa.Uuid(), nullable=True))
    op.add_column('refresh_tokens', sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('refresh_tokens', sa.Column('revoked_reason', sa.String(length=20), nullable=True))

    # Existing tokens each become their own single-token family.
    op.execute("UPDATE refresh_tokens SET family_id = id WHERE family_id IS NULL")
    op.alter_column('refresh_tokens', 'family_id', existing_type=sa.Uuid(), nullable=False)
    op.create_index('ix_refresh_tokens_family_id', 'refresh_tokens', ['family_id'])
    op.execute("UPDATE refresh_tokens SET revoked_reason = 'logout' "
               "WHERE revoked_at IS NOT NULL AND revoked_reason IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_refresh_tokens_family_id', table_name='refresh_tokens')
    op.drop_column('refresh_tokens', 'revoked_reason')
    op.drop_column('refresh_tokens', 'rotated_at')
    op.drop_column('refresh_tokens', 'family_id')
