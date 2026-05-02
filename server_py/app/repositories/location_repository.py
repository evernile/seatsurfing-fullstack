from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class LocationRow:
    id: str
    organization_id: str
    name: str
    map_mimetype: str
    map_width: int
    map_height: int
    map_scale: float
    description: str
    max_concurrent_bookings: int
    timezone: str
    enabled: bool


@dataclass
class LocationMapRow:
    mime_type: str
    data: Optional[bytes]
    width: int
    height: int
    scale: float


class LocationRepository:
    def create(
        self,
        db: Session,
        organization_id: str,
        name: str,
        description: str = "",
        max_concurrent_bookings: int = 0,
        timezone: str = "",
        enabled: bool = True,
    ) -> str:
        location_id = db.execute(
            text("""
                INSERT INTO locations
                    (organization_id, name, description, max_concurrent_bookings, tz, enabled)
                VALUES
                    (:org_id, :name, :description, :max_concurrent_bookings, :tz, :enabled)
                RETURNING id
            """),
            {
                "org_id": organization_id,
                "name": name,
                "description": description or "",
                "max_concurrent_bookings": int(max_concurrent_bookings or 0),
                "tz": timezone or "",
                "enabled": bool(enabled),
            },
        ).scalar_one()

        db.commit()
        return str(location_id)

    def get_one(self, db: Session, location_id: str) -> Optional[LocationRow]:
        row = db.execute(
            text("""
                SELECT
                    id,
                    organization_id,
                    name,
                    map_mimetype,
                    map_width,
                    map_height,
                    map_scale,
                    description,
                    max_concurrent_bookings,
                    COALESCE(tz, '') AS tz,
                    enabled
                FROM locations
                WHERE id = :id
            """),
            {"id": location_id},
        ).mappings().first()

        if not row:
            return None

        return LocationRow(
            id=str(row["id"]),
            organization_id=str(row["organization_id"]),
            name=row["name"],
            map_mimetype=row["map_mimetype"] or "",
            map_width=int(row["map_width"] or 0),
            map_height=int(row["map_height"] or 0),
            map_scale=float(row["map_scale"] or 1.0),
            description=row["description"] or "",
            max_concurrent_bookings=int(row["max_concurrent_bookings"] or 0),
            timezone=row["tz"] or "",
            enabled=bool(row["enabled"]),
        )

    def get_all(self, db: Session, organization_id: str) -> list[LocationRow]:
        rows = db.execute(
            text("""
                SELECT
                    id,
                    organization_id,
                    name,
                    map_mimetype,
                    map_width,
                    map_height,
                    map_scale,
                    description,
                    max_concurrent_bookings,
                    COALESCE(tz, '') AS tz,
                    enabled
                FROM locations
                WHERE organization_id = :org_id
                ORDER BY name
            """),
            {"org_id": organization_id},
        ).mappings().all()

        return [
            LocationRow(
                id=str(r["id"]),
                organization_id=str(r["organization_id"]),
                name=r["name"],
                map_mimetype=r["map_mimetype"] or "",
                map_width=int(r["map_width"] or 0),
                map_height=int(r["map_height"] or 0),
                map_scale=float(r["map_scale"] or 1.0),
                description=r["description"] or "",
                max_concurrent_bookings=int(r["max_concurrent_bookings"] or 0),
                timezone=r["tz"] or "",
                enabled=bool(r["enabled"]),
            )
            for r in rows
        ]

    def get_by_keyword(self, db: Session, organization_id: str, keyword: str) -> list[LocationRow]:
        kw = (keyword or "").strip().lower()

        rows = db.execute(
            text("""
                SELECT
                    id,
                    organization_id,
                    name,
                    map_mimetype,
                    map_width,
                    map_height,
                    map_scale,
                    description,
                    max_concurrent_bookings,
                    COALESCE(tz, '') AS tz,
                    enabled
                FROM locations
                WHERE organization_id = :org_id
                  AND LOWER(name) LIKE '%' || :kw || '%'
                ORDER BY name
            """),
            {"org_id": organization_id, "kw": kw},
        ).mappings().all()

        return [
            LocationRow(
                id=str(r["id"]),
                organization_id=str(r["organization_id"]),
                name=r["name"],
                map_mimetype=r["map_mimetype"] or "",
                map_width=int(r["map_width"] or 0),
                map_height=int(r["map_height"] or 0),
                map_scale=float(r["map_scale"] or 1.0),
                description=r["description"] or "",
                max_concurrent_bookings=int(r["max_concurrent_bookings"] or 0),
                timezone=r["tz"] or "",
                enabled=bool(r["enabled"]),
            )
            for r in rows
        ]

    def count(self, db: Session, organization_id: str) -> int:
        return int(
            db.execute(
                text("""
                    SELECT COUNT(id)
                    FROM locations
                    WHERE organization_id = :org_id
                """),
                {"org_id": organization_id},
            ).scalar_one()
        )

    def update(
        self,
        db: Session,
        location_id: str,
        organization_id: str,
        name: str,
        description: str,
        max_concurrent_bookings: int,
        map_scale: float,
        timezone: str,
        enabled: bool,
    ) -> None:
        db.execute(
            text("""
                UPDATE locations SET
                    organization_id = :org_id,
                    name = :name,
                    description = :description,
                    max_concurrent_bookings = :max_concurrent_bookings,
                    map_scale = :map_scale,
                    tz = :tz,
                    enabled = :enabled
                WHERE id = :id
            """),
            {
                "org_id": organization_id,
                "name": name,
                "description": description or "",
                "max_concurrent_bookings": int(max_concurrent_bookings or 0),
                "map_scale": float(map_scale or 1.0),
                "tz": timezone or "",
                "enabled": bool(enabled),
                "id": location_id,
            },
        )
        db.commit()

    def set_map(
        self,
        db: Session,
        location_id: str,
        mime_type: str,
        data: Optional[bytes],
        width: int,
        height: int,
        scale: float,
    ) -> None:
        db.execute(
            text("""
                UPDATE locations SET
                    map_mimetype = :mime,
                    map_data = :data,
                    map_width = :w,
                    map_height = :h,
                    map_scale = :scale
                WHERE id = :id
            """),
            {
                "mime": mime_type or "",
                "data": data,
                "w": int(width or 0),
                "h": int(height or 0),
                "scale": float(scale or 1.0),
                "id": location_id,
            },
        )
        db.commit()

    def get_map(self, db: Session, location_id: str) -> Optional[LocationMapRow]:
        row = db.execute(
            text("""
                SELECT map_mimetype, map_data, map_width, map_height, map_scale
                FROM locations
                WHERE id = :id
            """),
            {"id": location_id},
        ).mappings().first()

        if not row:
            return None

        return LocationMapRow(
            mime_type=row["map_mimetype"] or "",
            data=row["map_data"],
            width=int(row["map_width"] or 0),
            height=int(row["map_height"] or 0),
            scale=float(row["map_scale"] or 1.0),
        )

    def delete(self, db: Session, location_id: str) -> None:
        db.execute(
            text("""
                DELETE FROM bookings
                WHERE bookings.space_id IN (
                    SELECT spaces.id FROM spaces WHERE spaces.location_id = :loc_id
                )
            """),
            {"loc_id": location_id},
        )

        db.execute(
            text("""
                DELETE FROM spaces
                WHERE location_id = :loc_id
            """),
            {"loc_id": location_id},
        )

        db.execute(
            text("""
                DELETE FROM space_attribute_values
                WHERE entity_id = :loc_id
                  AND entity_type = :entity_type
            """),
            {"loc_id": location_id, "entity_type": "location"},
        )

        db.execute(
            text("""
                DELETE FROM locations
                WHERE id = :loc_id
            """),
            {"loc_id": location_id},
        )

        db.commit()

    def delete_all(self, db: Session, organization_id: str) -> None:
        db.execute(
            text("""
                DELETE FROM bookings
                WHERE bookings.space_id IN (
                    SELECT spaces.id FROM spaces
                    WHERE spaces.location_id IN (
                        SELECT locations.id FROM locations
                        WHERE locations.organization_id = :org_id
                    )
                )
            """),
            {"org_id": organization_id},
        )

        db.execute(
            text("""
                DELETE FROM recurring_bookings
                WHERE recurring_bookings.space_id IN (
                    SELECT spaces.id FROM spaces
                    WHERE spaces.location_id IN (
                        SELECT locations.id FROM locations
                        WHERE locations.organization_id = :org_id
                    )
                )
            """),
            {"org_id": organization_id},
        )

        db.execute(
            text("""
                DELETE FROM space_attribute_values
                WHERE attribute_id IN (
                    SELECT id FROM space_attributes WHERE organization_id = :org_id
                )
            """),
            {"org_id": organization_id},
        )

        db.execute(
            text("""
                DELETE FROM space_attributes
                WHERE organization_id = :org_id
            """),
            {"org_id": organization_id},
        )

        db.execute(
            text("""
                DELETE FROM spaces
                WHERE spaces.location_id IN (
                    SELECT locations.id FROM locations WHERE locations.organization_id = :org_id
                )
            """),
            {"org_id": organization_id},
        )

        db.execute(
            text("""
                DELETE FROM locations
                WHERE organization_id = :org_id
            """),
            {"org_id": organization_id},
        )

        db.commit()