"""add locations and space location_id

Revision ID: 880434a8a2be
Revises: 5c0dd0931a0e
Create Date: 2026-02-10 11:46:55.210460
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "880434a8a2be"
down_revision: Union[str, Sequence[str], None] = "5c0dd0931a0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) CREA locations se non esiste (perché gli ALTER sotto falliscono se manca)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id UUID PRIMARY KEY,
            organization_id VARCHAR NOT NULL REFERENCES organizations(id),
            name VARCHAR NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_locations_id ON locations(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_locations_organization_id ON locations(organization_id)")

    # 2) locations: aggiunta colonne "Go-like" (idempotente)
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS map_mimetype VARCHAR NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS map_data BYTEA")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS map_width INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS map_height INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS map_scale REAL NOT NULL DEFAULT 1.0")

    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS description VARCHAR NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS max_concurrent_bookings INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS timezone VARCHAR NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE locations ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE")

    # 3) spaces.location_id (idempotente)
    op.execute("ALTER TABLE spaces ADD COLUMN IF NOT EXISTS location_id UUID")
    op.execute("CREATE INDEX IF NOT EXISTS ix_spaces_location_id ON spaces(location_id)")

    # 4) FK spaces.location_id -> locations.id (idempotente via try/drop+create)
    # Postgres non ha "ADD CONSTRAINT IF NOT EXISTS" per tutti i casi -> facciamo safe drop + create
    op.execute("ALTER TABLE spaces DROP CONSTRAINT IF EXISTS fk_spaces_location_id")
    op.execute(
        """
        ALTER TABLE spaces
        ADD CONSTRAINT fk_spaces_location_id
        FOREIGN KEY (location_id) REFERENCES locations(id)
        """
    )


def downgrade() -> None:
    # rollback FK/colonna su spaces
    op.execute("ALTER TABLE spaces DROP CONSTRAINT IF EXISTS fk_spaces_location_id")
    op.execute("DROP INDEX IF EXISTS ix_spaces_location_id")
    op.execute("ALTER TABLE spaces DROP COLUMN IF EXISTS location_id")

    # rollback colonne "extra" su locations (non droppo la tabella per sicurezza, ma se vuoi si può)
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS enabled")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS timezone")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS max_concurrent_bookings")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS description")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS map_scale")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS map_height")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS map_width")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS map_data")
    op.execute("ALTER TABLE locations DROP COLUMN IF EXISTS map_mimetype")

    # indici locations (opzionale)
    op.execute("DROP INDEX IF EXISTS ix_locations_organization_id")
    op.execute("DROP INDEX IF EXISTS ix_locations_id")

    # Se vuoi proprio eliminare locations:
    # op.execute("DROP TABLE IF EXISTS locations")