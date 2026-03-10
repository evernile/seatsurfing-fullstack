from alembic import op
import sqlalchemy as sa

revision = "3511bfdc1d1c"
down_revision = "95bc6323cbe7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) aggiungi la colonna (DEVE esistere prima della FK)
    op.add_column(
        "users",
        sa.Column("organization_id", sa.String(), nullable=True)
    )

    # 2) indice (se lo vuoi)
    op.create_index(op.f("ix_users_organization_id"), "users", ["organization_id"], unique=False)

    # 3) FK
    op.create_foreign_key(
        "fk_users_organization",
        "users",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_organization", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_organization_id"), table_name="users")
    op.drop_column("users", "organization_id")