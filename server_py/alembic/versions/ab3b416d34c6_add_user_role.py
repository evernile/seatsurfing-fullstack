"""add user role

Revision ID: ab3b416d34c6
Revises: 231c3ff0959f
Create Date: 2026-02-09 20:00:26.662627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab3b416d34c6'
down_revision: Union[str, Sequence[str], None] = '231c3ff0959f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('role', sa.String(), nullable=True))

    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")

    op.alter_column("users", "role", nullable=False)

    

def downgrade() -> None:
    """Downgrade schema."""
    
    op.drop_column('users', 'role')
    