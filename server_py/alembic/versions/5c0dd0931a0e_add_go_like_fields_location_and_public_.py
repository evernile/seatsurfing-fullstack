"""add go-like fields location and public ids

Revision ID: 5c0dd0931a0e
Revises: ab3b416d34c6
Create Date: 2026-02-10 10:45:28.665301
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5c0dd0931a0e"
down_revision: Union[str, Sequence[str], None] = "ab3b416d34c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # UUID support
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # 0) USERS: aggiungi public_id (serve per FK users_groups -> users.public_id)
    op.add_column(
        "users",
        sa.Column(
            "public_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
    )
    op.create_index("ix_users_public_id", "users", ["public_id"], unique=True)

    # 1) LOCATIONS (allineata ai models.py)
    op.create_table(
        "locations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("organization_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),

        sa.Column("map_mimetype", sa.String(), nullable=False, server_default=""),
        sa.Column("map_data", sa.LargeBinary(), nullable=True),
        sa.Column("map_width", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("map_height", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("map_scale", sa.Float(), nullable=False, server_default="1.0"),

        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("max_concurrent_bookings", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("timezone", sa.String(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    )
    op.create_index("ix_locations_organization_id", "locations", ["organization_id"], unique=False)

    # 2) SPACES: aggiungi location_id UUID e FK
    op.add_column("spaces", sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_spaces_location_id", "spaces", ["location_id"], unique=False)
    op.create_foreign_key(
        "fk_spaces_location_id",
        "spaces",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    # spaces.location_id
    op.drop_constraint("fk_spaces_location_id", "spaces", type_="foreignkey")
    op.drop_index("ix_spaces_location_id", table_name="spaces")
    op.drop_column("spaces", "location_id")

    # locations
    op.drop_index("ix_locations_organization_id", table_name="locations")
    op.drop_table("locations")

    # users.public_id
    op.drop_index("ix_users_public_id", table_name="users")
    op.drop_column("users", "public_id")