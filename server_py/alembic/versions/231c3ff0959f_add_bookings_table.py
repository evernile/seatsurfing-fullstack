"""add bookings table

Revision ID: 231c3ff0959f
Revises: e4cff7f40c6e
Create Date: 2026-02-09 17:02:03.860987
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "231c3ff0959f"
down_revision: Union[str, Sequence[str], None] = "e4cff7f40c6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column("organization_id", sa.String(), nullable=False),

        # DEVE essere UUID perché spaces.id è UUID
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("user_id", sa.Integer(), nullable=False),

        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),

        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_bookings_end_at", "bookings", ["end_at"], unique=False)
    op.create_index("ix_bookings_id", "bookings", ["id"], unique=False)
    op.create_index("ix_bookings_is_active", "bookings", ["is_active"], unique=False)
    op.create_index("ix_bookings_organization_id", "bookings", ["organization_id"], unique=False)
    op.create_index("ix_bookings_space_id", "bookings", ["space_id"], unique=False)
    op.create_index("ix_bookings_start_at", "bookings", ["start_at"], unique=False)
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_index("ix_bookings_start_at", table_name="bookings")
    op.drop_index("ix_bookings_space_id", table_name="bookings")
    op.drop_index("ix_bookings_organization_id", table_name="bookings")
    op.drop_index("ix_bookings_is_active", table_name="bookings")
    op.drop_index("ix_bookings_id", table_name="bookings")
    op.drop_index("ix_bookings_end_at", table_name="bookings")
    op.drop_table("bookings")