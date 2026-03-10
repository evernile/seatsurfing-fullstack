"""add booking status and approval fields

Revision ID: a9833fba46cd
Revises: 1bc7c6b8938c
Create Date: 2026-02-18 11:17:43.105452
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a9833fba46cd"
down_revision: Union[str, Sequence[str], None] = "1bc7c6b8938c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) status con default per non rompere righe già esistenti
    op.add_column(
        "bookings",
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'approved'"),
        ),
    )

    # 2) campi approvazione
    op.add_column(
        "bookings",
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "bookings",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3) indici utili
    op.create_index("ix_bookings_status", "bookings", ["status"], unique=False)
    op.create_index("ix_bookings_approved_by", "bookings", ["approved_by"], unique=False)

    # 4) FK approved_by -> users.public_id
    op.create_foreign_key(
        "fk_bookings_approved_by_users_public_id",
        "bookings",
        "users",
        ["approved_by"],
        ["public_id"],
        ondelete="SET NULL",
    )

    # 5) (consigliato) togli il default dopo la migrazione
    op.alter_column("bookings", "status", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "fk_bookings_approved_by_users_public_id",
        "bookings",
        type_="foreignkey",
    )
    op.drop_index("ix_bookings_approved_by", table_name="bookings")
    op.drop_index("ix_bookings_status", table_name="bookings")
    op.drop_column("bookings", "approved_at")
    op.drop_column("bookings", "approved_by")
    op.drop_column("bookings", "status")