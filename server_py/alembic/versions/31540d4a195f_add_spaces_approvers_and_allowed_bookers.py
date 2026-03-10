"""add spaces_approvers and spaces_allowed_bookers

Revision ID: 31540d4a195f
Revises: 5c0dd0931a0e
Create Date: 2026-02-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "31540d4a195f"
down_revision: Union[str, Sequence[str], None] = "5c0dd0931a0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spaces_approvers",
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("space_id", "group_id", name="pk_spaces_approvers"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.public_id"], ondelete="CASCADE"),
    )

    op.create_table(
        "spaces_allowed_bookers",
        sa.Column("space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("space_id", "group_id", name="pk_spaces_allowed_bookers"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.public_id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("spaces_allowed_bookers")
    op.drop_table("spaces_approvers")