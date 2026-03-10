# app/repositories/space_attribute_repository.py

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional
import threading

from sqlalchemy import text
from sqlalchemy.orm import Session


# --- Go: SettingType (server/api) ---
# Nel Go è un int; qui lo modelliamo come IntEnum.
# IMPORTANT: il default usato dal Go è SettingTypeString.
class SettingType(IntEnum):
    SettingTypeString = 0
    SettingTypeInt = 1
    SettingTypeBool = 2


@dataclass
class SpaceAttribute:
    ID: str = ""
    OrganizationID: str = ""
    Label: str = ""
    Type: int = int(SettingType.SettingTypeString)
    SpaceApplicable: bool = False
    LocationApplicable: bool = False


class SpaceAttributeRepository:
    """
    Porting 1:1 di space-attribute-repository.go
    NOTE:
    - In Go la table viene creata dentro GetSpaceAttributeRepository()
      tramite GetDatabase().DB().Exec(...)
    - In Python non abbiamo GetDatabase() globale uguale: quindi forniamo ensure_table(db)
      da chiamare in startup/seed (come hai fatto per settings).
    """

    def ensure_table(self, db: Session) -> None:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS space_attributes ("
                "id uuid DEFAULT uuid_generate_v4(), "
                "organization_id uuid NOT NULL, "
                "label VARCHAR NOT NULL, "
                f"type INTEGER DEFAULT {int(SettingType.SettingTypeString)}, "
                "space_applicable boolean NOT NULL DEFAULT FALSE, "
                "location_applicable boolean NOT NULL DEFAULT FALSE, "
                "PRIMARY KEY (id))"
            )
        )
        db.commit()

    def run_schema_upgrade(self, cur_version: int, target_version: int) -> None:
        # Go: // nothing yet
        return

    def create(self, db: Session, e: SpaceAttribute) -> SpaceAttribute:
        row = db.execute(
            text(
                "INSERT INTO space_attributes "
                "(organization_id, label, type, space_applicable, location_applicable) "
                "VALUES (:organization_id, :label, :type, :space_applicable, :location_applicable) "
                "RETURNING id"
            ),
            {
                "organization_id": e.OrganizationID,
                "label": e.Label,
                "type": int(e.Type),
                "space_applicable": bool(e.SpaceApplicable),
                "location_applicable": bool(e.LocationApplicable),
            },
        ).fetchone()
        db.commit()
        e.ID = str(row[0])
        return e

    def get_one(self, db: Session, id_: str) -> Optional[SpaceAttribute]:
        row = db.execute(
            text(
                "SELECT id, organization_id, label, type, space_applicable, location_applicable "
                "FROM space_attributes "
                "WHERE id = :id"
            ),
            {"id": id_},
        ).fetchone()

        if not row:
            return None

        return SpaceAttribute(
            ID=str(row[0]),
            OrganizationID=str(row[1]),
            Label=str(row[2]),
            Type=int(row[3]) if row[3] is not None else int(SettingType.SettingTypeString),
            SpaceApplicable=bool(row[4]),
            LocationApplicable=bool(row[5]),
        )

    def get_all(self, db: Session, organization_id: str) -> List[SpaceAttribute]:
        rows = db.execute(
            text(
                "SELECT id, organization_id, label, type, space_applicable, location_applicable "
                "FROM space_attributes "
                "WHERE organization_id = :org_id "
                "ORDER BY label"
            ),
            {"org_id": organization_id},
        ).fetchall()

        result: List[SpaceAttribute] = []
        for r in rows:
            result.append(
                SpaceAttribute(
                    ID=str(r[0]),
                    OrganizationID=str(r[1]),
                    Label=str(r[2]),
                    Type=int(r[3]) if r[3] is not None else int(SettingType.SettingTypeString),
                    SpaceApplicable=bool(r[4]),
                    LocationApplicable=bool(r[5]),
                )
            )
        return result

    def update(self, db: Session, e: SpaceAttribute) -> None:
        db.execute(
            text(
                "UPDATE space_attributes SET "
                "organization_id = :organization_id, "
                "label = :label, "
                "type = :type, "
                "space_applicable = :space_applicable, "
                "location_applicable = :location_applicable "
                "WHERE id = :id"
            ),
            {
                "organization_id": e.OrganizationID,
                "label": e.Label,
                "type": int(e.Type),
                "space_applicable": bool(e.SpaceApplicable),
                "location_applicable": bool(e.LocationApplicable),
                "id": e.ID,
            },
        )
        db.commit()

    def delete(self, db: Session, e: SpaceAttribute) -> None:
        # Go:
        # DELETE FROM space_attribute_values WHERE attribute_id = $1
        db.execute(
            text("DELETE FROM space_attribute_values WHERE attribute_id = :attr_id"),
            {"attr_id": e.ID},
        )
        # DELETE FROM space_attributes WHERE id = $1
        db.execute(
            text("DELETE FROM space_attributes WHERE id = :id"),
            {"id": e.ID},
        )
        db.commit()


# --- singleton (Go: var + sync.Once) ---
_space_attribute_repository: Optional[SpaceAttributeRepository] = None
_space_attribute_lock = threading.Lock()


def get_space_attribute_repository() -> SpaceAttributeRepository:
    global _space_attribute_repository
    if _space_attribute_repository is None:
        with _space_attribute_lock:
            if _space_attribute_repository is None:
                _space_attribute_repository = SpaceAttributeRepository()
    return _space_attribute_repository