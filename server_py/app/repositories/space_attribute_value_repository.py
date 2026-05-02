from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional
import threading

from sqlalchemy import text
from sqlalchemy.orm import Session


class SpaceAttributeValueEntityType(IntEnum):
    SpaceAttributeValueEntityTypeLocation = 1
    SpaceAttributeValueEntityTypeSpace = 2


@dataclass
class SpaceAttributeValue:
    AttributeID: str = ""
    EntityID: str = ""
    EntityType: int = 0
    Value: str = ""


class SpaceAttributeValueRepository:
    """
    Porting diretto di space-attribute-value-repository.go
    """

    def ensure_table(self, db: Session) -> None:
        db.execute(
            text(
                "CREATE TABLE IF NOT EXISTS space_attribute_values ("
                "attribute_id uuid NOT NULL, "
                "entity_id uuid NOT NULL, "
                "entity_type INTEGER NOT NULL, "
                "value VARCHAR NOT NULL DEFAULT '', "
                "PRIMARY KEY (attribute_id, entity_id, entity_type))"
            )
        )
        db.commit()

    def run_schema_upgrade(self, cur_version: int, target_version: int) -> None:
        
        return

    def set(
        self,
        db: Session,
        attribute_id: str,
        entity_id: str,
        entity_type: SpaceAttributeValueEntityType,
        value: str,
    ) -> None:
        db.execute(
            text(
                "INSERT INTO space_attribute_values "
                "(attribute_id, entity_id, entity_type, value) "
                "VALUES (:attribute_id, :entity_id, :entity_type, :value) "
                "ON CONFLICT (attribute_id, entity_id, entity_type) "
                "DO UPDATE SET value = :value"
            ),
            {
                "attribute_id": attribute_id,
                "entity_id": entity_id,
                "entity_type": int(entity_type),
                "value": value,
            },
        )
        db.commit()

    def get(
        self,
        db: Session,
        attribute_id: str,
        entity_id: str,
        entity_type: SpaceAttributeValueEntityType,
    ) -> Optional[str]:
        row = db.execute(
            text(
                "SELECT value FROM space_attribute_values "
                "WHERE attribute_id = :attribute_id "
                "AND entity_id = :entity_id "
                "AND entity_type = :entity_type"
            ),
            {
                "attribute_id": attribute_id,
                "entity_id": entity_id,
                "entity_type": int(entity_type),
            },
        ).fetchone()

        if not row:
            return None

        return str(row[0])

    def get_all_for_entity(
        self,
        db: Session,
        entity_id: str,
        entity_type: SpaceAttributeValueEntityType,
    ) -> List[SpaceAttributeValue]:
        return self.get_all_for_entity_list(db, [entity_id], entity_type)

    def get_all_for_entity_list(
        self,
        db: Session,
        entity_ids: List[str],
        entity_type: SpaceAttributeValueEntityType,
    ) -> List[SpaceAttributeValue]:
        rows = db.execute(
            text(
                "SELECT attribute_id, entity_id, entity_type, value "
                "FROM space_attribute_values "
                "WHERE entity_id = ANY(:entity_ids) AND entity_type = :entity_type"
            ),
            {
                "entity_ids": entity_ids,
                "entity_type": int(entity_type),
            },
        ).fetchall()

        result: List[SpaceAttributeValue] = []

        for r in rows:
            result.append(
                SpaceAttributeValue(
                    AttributeID=str(r[0]),
                    EntityID=str(r[1]),
                    EntityType=int(r[2]),
                    Value=str(r[3]),
                )
            )

        return result

    def get_all(
        self,
        db: Session,
        organization_id: str,
        entity_type: SpaceAttributeValueEntityType,
    ) -> List[SpaceAttributeValue]:

        join = "LEFT JOIN locations ON space_attribute_values.entity_id = locations.id"

        if entity_type == SpaceAttributeValueEntityType.SpaceAttributeValueEntityTypeSpace:
            join = (
                "LEFT JOIN spaces ON space_attribute_values.entity_id = spaces.id "
                + join
            )

        rows = db.execute(
            text(
                "SELECT attribute_id, entity_id, entity_type, value "
                "FROM space_attribute_values "
                + join
                + " "
                "WHERE organization_id = :organization_id "
                "AND entity_type = :entity_type"
            ),
            {
                "organization_id": organization_id,
                "entity_type": int(entity_type),
            },
        ).fetchall()

        result: List[SpaceAttributeValue] = []

        for r in rows:
            result.append(
                SpaceAttributeValue(
                    AttributeID=str(r[0]),
                    EntityID=str(r[1]),
                    EntityType=int(r[2]),
                    Value=str(r[3]),
                )
            )

        return result

    def delete(
        self,
        db: Session,
        attribute_id: str,
        entity_id: str,
        entity_type: SpaceAttributeValueEntityType,
    ) -> None:
        db.execute(
            text(
                "DELETE FROM space_attribute_values "
                "WHERE attribute_id = :attribute_id "
                "AND entity_id = :entity_id "
                "AND entity_type = :entity_type"
            ),
            {
                "attribute_id": attribute_id,
                "entity_id": entity_id,
                "entity_type": int(entity_type),
            },
        )
        db.commit()


_space_attribute_value_repository: Optional[SpaceAttributeValueRepository] = None
_lock = threading.Lock()


def get_space_attribute_value_repository() -> SpaceAttributeValueRepository:
    global _space_attribute_value_repository

    if _space_attribute_value_repository is None:
        with _lock:
            if _space_attribute_value_repository is None:
                _space_attribute_value_repository = SpaceAttributeValueRepository()

    return _space_attribute_value_repository