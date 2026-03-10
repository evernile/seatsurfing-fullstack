from __future__ import annotations

import base64
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.repositories.location_repository import LocationRepository

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Location, Space

repo = LocationRepository()

router = APIRouter(prefix="/location", tags=["ui-compat"])



class SearchAttribute(BaseModel):
    attributeId: str
    op: str | None = None
    value: str | None = None


class SearchLocationRequest(BaseModel):
    enter: str
    leave: str
    attributes: list[SearchAttribute] = []


def _location_to_ui(e: Location) -> dict[str, Any]:
    return {
        "id": str(e.id),
        "organizationId": str(getattr(e, "organization_id", "")),
        "name": e.name,
        "description": getattr(e, "description", "") or "",
        "timezone": getattr(e, "timezone", None) or getattr(e, "tz", None) or "Europe/Rome",
        "enabled": bool(getattr(e, "enabled", True)),
        "maxConcurrentBookings": int(getattr(e, "max_concurrent_bookings", 0) or 0),
        "mapWidth": int(getattr(e, "map_width", 0) or 0),
        "mapHeight": int(getattr(e, "map_height", 0) or 0),
        "mapScale": float(getattr(e, "map_scale", 1) or 1),
        "mapMimeType": getattr(e, "map_mimetype", "") or "",
    }


@router.get("/")
def list_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(Location)
        .filter(Location.organization_id == current_user.organization_id)
        .all()
    )
    return [_location_to_ui(e) for e in items]


@router.get("/{location_id}")
def get_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = (
        db.query(Location)
        .filter(
            Location.id == location_id,
            Location.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")
    return _location_to_ui(e)


@router.get("/{location_id}/map")
def get_location_map(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = (
        db.query(Location)
        .filter(
            Location.id == location_id,
            Location.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")

    raw_data = getattr(e, "map_data", None)
    raw_width = getattr(e, "map_width", 0)
    raw_height = getattr(e, "map_height", 0)
    raw_scale = getattr(e, "map_scale", 1)
    raw_mime = getattr(e, "map_mimetype", "") or ""

    data_b64 = ""
    if raw_data:
        try:
            data_b64 = base64.b64encode(raw_data).decode("utf-8")
        except Exception:
            data_b64 = ""

    return {
        "width": int(raw_width or 0),
        "height": int(raw_height or 0),
        "scale": float(raw_scale or 1),
        "mimeType": raw_mime,
        "data": data_b64,
    }


@router.post("/search")
def search_locations(
    payload: SearchLocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    items = (
        db.query(Location)
        .filter(Location.organization_id == current_user.organization_id)
        .all()
    )
    return [_location_to_ui(e) for e in items]



@router.get("/{location_id}/space/availability")
def availability_by_location_space(
    location_id: str,
    enter: str | None = None,
    leave: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = (
        db.query(Location)
        .filter(
            Location.id == location_id,
            Location.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")

    spaces = (
        db.query(Space)
        .filter(Space.location_id == uuid.UUID(location_id))
        .all()
    )

    return [
    {
        "id": str(s.id),
        "name": s.name,
        "x": int(getattr(s, "x", 0) or 0),
        "y": int(getattr(s, "y", 0) or 0),
        "width": int(getattr(s, "width", 0) or 0),
        "height": int(getattr(s, "height", 0) or 0),
        "rotation": int(getattr(s, "rotation", 0) or 0),

        "booked": False,
        "selfBooked": False,
        "buddyBooked": False,
        "partiallyBooked": False,
        "allowed": True,
        "pendingApproval": False,
        "available": True,
    }
    for s in spaces
]


@router.get("/{location_id}/availability")
def availability_by_location(
    location_id: str,
    enter: str | None = None,
    leave: str | None = None,
    current_user: User = Depends(get_current_user),
):
    
    return []


@router.get("/{location_id}/attribute")
def get_location_attributes(
    location_id: str,
    current_user: User = Depends(get_current_user),
):
    return []


@router.post("/{location_id}/attribute/{attribute_id}")
def set_location_attribute(
    location_id: str,
    attribute_id: str,
    current_user: User = Depends(get_current_user),
):
    return {"status": "updated"}


@router.delete("/{location_id}/attribute/{attribute_id}")
def delete_location_attribute(
    location_id: str,
    attribute_id: str,
    current_user: User = Depends(get_current_user),
):
    return {"status": "updated"}