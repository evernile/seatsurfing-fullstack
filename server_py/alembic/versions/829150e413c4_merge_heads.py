"""merge heads

Revision ID: 829150e413c4
Revises: 31540d4a195f, 880434a8a2be
Create Date: 2026-02-10 15:01:12.561110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '829150e413c4'
down_revision: Union[str, Sequence[str], None] = ('31540d4a195f', '880434a8a2be')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
