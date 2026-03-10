"""create organizations table

Revision ID: 95bc6323cbe7
Revises: 7a36d334ce85
Create Date: 2026-02-04 16:05:04.600946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95bc6323cbe7'
down_revision: Union[str, Sequence[str], None] = '7a36d334ce85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
    )



def downgrade() -> None:
    op.drop_table("organizations")

