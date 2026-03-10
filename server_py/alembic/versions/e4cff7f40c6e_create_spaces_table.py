"""create spaces table

Revision ID: e4cff7f40c6e
Revises: 3511bfdc1d1c
Create Date: 2026-02-09 11:16:51.632947
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e4cff7f40c6e"
down_revision: Union[str, Sequence[str], None] = "3511bfdc1d1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("organization_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),

        sa.Column("kind", sa.String(), nullable=False, server_default="desk"),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id", name="uq_spaces_public_id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )

    op.create_index("ix_spaces_id", "spaces", ["id"], unique=False)
    op.create_index("ix_spaces_public_id", "spaces", ["public_id"], unique=True)
    op.create_index("ix_spaces_organization_id", "spaces", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_spaces_organization_id", table_name="spaces")
    op.drop_index("ix_spaces_public_id", table_name="spaces")
    op.drop_index("ix_spaces_id", table_name="spaces")
    op.drop_table("spaces")