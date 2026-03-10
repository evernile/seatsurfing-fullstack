"""add groups and users_groups

Revision ID: 1bc7c6b8938c
Revises: 829150e413c4
Create Date: 2026-02-17 17:16:16.622470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1bc7c6b8938c'
down_revision: Union[str, Sequence[str], None] = '829150e413c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_groups_org_name"),
    )
    op.create_index("ix_groups_organization_id", "groups", ["organization_id"])

    op.create_table(
        "users_groups",
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("group_id", "user_id", name="pk_users_groups"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.public_id"], ondelete="CASCADE"),
    )
    op.create_index("ix_users_groups_user_id", "users_groups", ["user_id"])
    op.create_index("ix_users_groups_group_id", "users_groups", ["group_id"])


def downgrade():
    op.drop_index("ix_users_groups_group_id", table_name="users_groups")
    op.drop_index("ix_users_groups_user_id", table_name="users_groups")
    op.drop_table("users_groups")
    op.drop_index("ix_groups_organization_id", table_name="groups")
    op.drop_table("groups")
