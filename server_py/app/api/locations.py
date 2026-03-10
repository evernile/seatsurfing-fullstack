import base64
import re
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from fastapi import Request

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Location, User
from app.repositories.location_repository import LocationRepository
from app.schemas.location import (
    CreateLocationRequest,
    GetLocationResponse,
    GetMapResponse,
    SearchLocationRequest,
)

router = APIRouter(prefix="/locations", tags=["locations"])
repo = LocationRepository()

# --- Helpers "Go-like" ---
def can_access_org(user: User, organization_id: str) -> bool:
    return bool(user.organization_id) and (user.role in ("admin", "org_admin", "super_admin"))

def can_space_admin_org(user: User, organization_id: str) -> bool:
    # admin può gestire locations/spaces.
    return can_access_org(user, organization_id) and (user.role == "admin")

def is_valid_timezone(tz: str) -> bool:
    
    return isinstance(tz, str) and len(tz) <= 64

def detect_image_type_and_size(data: bytes) -> tuple[str, int, int]:
    """
    Minimal parser:
    - PNG: legge IHDR
    - JPEG: prova a scorrere segmenti per trovare SOF0/SOF2 (dimensioni)
    - GIF: width/height da header
    - SVG: prova a leggere width/height o viewBox via regex
    """
    if len(data) < 10:
        raise ValueError("invalid image")

    # PNG
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        w = int.from_bytes(data[16:20], "big")
        h = int.from_bytes(data[20:24], "big")
        return ("png", w, h)

    # GIF
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        w = int.from_bytes(data[6:8], "little")
        h = int.from_bytes(data[8:10], "little")
        return ("gif", w, h)

    # JPEG
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i < len(data) - 1:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            # markers without length
            if marker in (0xD8, 0xD9):
                continue
            if i + 2 > len(data):
                break
            seg_len = int.from_bytes(data[i:i+2], "big")
            if seg_len < 2:
                break
            # SOF0, SOF2 (baseline/progressive)
            if marker in (0xC0, 0xC2) and i + 7 < len(data):
                h = int.from_bytes(data[i+3:i+5], "big")
                w = int.from_bytes(data[i+5:i+7], "big")
                return ("jpeg", w, h)
            i += seg_len
        return ("jpeg", 0, 0)

    # SVG (text)
    try:
        text = data.decode("utf-8", errors="ignore")
        if "<svg" in text:
            # width/height
            w = h = 0
            mw = re.search(r'width="([\d\.]+)', text)
            mh = re.search(r'height="([\d\.]+)', text)
            if mw:
                w = int(float(mw.group(1)))
            if mh:
                h = int(float(mh.group(1)))
            if (w == 0 or h == 0):
                mvb = re.search(r'viewBox="([\d\.\s]+)"', text)
                if mvb:
                    parts = mvb.group(1).strip().split()
                    if len(parts) == 4:
                        w = int(float(parts[2]))
                        h = int(float(parts[3]))
            return ("svg+xml", w, h)
    except Exception:
        pass

    raise ValueError("unsupported image")


# --- Routes (Go router -> FastAPI) ---

@router.get("/", response_model=list[GetLocationResponse])
def get_all_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    items = repo.get_all(db, current_user.organization_id)
    return [
        GetLocationResponse(
            id=e.id,
            organizationId=e.organization_id,
            name=e.name,
            mapWidth=int(getattr(e, "map_width", 0) or 0),
            mapHeight=int(getattr(e, "map_height", 0) or 0),
            mapMimeType=str(getattr(e, "map_mimetype", "") or ""),
            description=str(getattr(e, "description", "") or ""),
            maxConcurrentBookings=int(getattr(e, "max_concurrent_bookings", 0) or 0),
            timezone=str(getattr(e, "tz", "") or ""),
            enabled=bool(getattr(e, "enabled", True)),
            mapScale=float(getattr(e, "map_scale", 1.0) or 1.0),
        )
        for e in items
    ]


@router.get("/{location_id}", response_model=GetLocationResponse)
def get_one_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = repo.get_one(db, location_id)
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")
    if not can_access_org(current_user, e.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    return GetLocationResponse(
        id=e.id,
        organizationId=e.organization_id,
        name=e.name,
        mapWidth=int(getattr(e, "map_width", 0) or 0),
        mapHeight=int(getattr(e, "map_height", 0) or 0),
        mapMimeType=str(getattr(e, "map_mimetype", "") or ""),
        description=str(getattr(e, "description", "") or ""),
        maxConcurrentBookings=int(getattr(e, "max_concurrent_bookings", 0) or 0),
        timezone=str(getattr(e, "tz", "") or ""),
        enabled=bool(getattr(e, "enabled", True)),
        mapScale=float(getattr(e, "map_scale", 1.0) or 1.0),
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_location(
    payload: CreateLocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    if not can_space_admin_org(current_user, current_user.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.timezone and not is_valid_timezone(payload.timezone):
        raise HTTPException(status_code=400, detail="Invalid timezone")

    e = Location(
        organization_id=current_user.organization_id,
        name=payload.name,
        description=payload.description,
        max_concurrent_bookings=payload.max_concurrent_bookings,
        timezone=payload.timezone,
        enabled=payload.enabled,
        map_scale=payload.map_scale,
    )
    e = repo.create(db, e)
    
    return {"id": e.id}


@router.put("/{location_id}", status_code=status.HTTP_200_OK)
def update_location(
    location_id: str,
    payload: CreateLocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = repo.get_one(db, location_id)
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")
    if not can_space_admin_org(current_user, e.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.timezone and not is_valid_timezone(payload.timezone):
        raise HTTPException(status_code=400, detail="Invalid timezone")

    e.name = payload.name
    e.description = payload.description
    e.max_concurrent_bookings = payload.max_concurrent_bookings
    e.timezone = payload.timezone
    e.enabled = payload.enabled
    e.map_scale = payload.map_scale

    repo.update(db, e)
    return {"status": "updated"}


@router.delete("/{location_id}", status_code=status.HTTP_200_OK)
def delete_location(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = repo.get_one(db, location_id)
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")
    if not can_space_admin_org(current_user, e.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    repo.delete(db, e)
    return {"status": "updated"}


@router.get("/{location_id}/map", response_model=GetMapResponse)
def get_map(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = repo.get_one(db, location_id)
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")
    if not can_access_org(current_user, e.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    m = repo.get_map(db, e)
    return GetMapResponse(
        width=m["width"],
        height=m["height"],
        scale=m["scale"],
        mimeType=m["mime_type"],
        data=base64.b64encode(m["data"]).decode("utf-8"),
    )


@router.post("/{location_id}/map", status_code=200)
async def set_map(
    location_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    e = repo.get_one(db, location_id)
    if not e:
        raise HTTPException(status_code=404, detail="Location not found")
    if not can_space_admin_org(current_user, e.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty body")

    try:
        mime, w, h = detect_image_type_and_size(data)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image (png/jpg/gif/svg only)")

    repo.set_map(db, e, mime_type=mime, data=data, width=w, height=h, scale=1.0)
    return {"status": "updated"}

@router.get("/{location_id}/attribute")
def get_attributes(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Not implemented yet (space_attribute_values)")


@router.post("/{location_id}/attribute/{attribute_id}", status_code=200)
def set_attribute(
    location_id: str,
    attribute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Not implemented yet (space_attribute_values)")


@router.delete("/{location_id}/attribute/{attribute_id}", status_code=200)
def delete_attribute(
    location_id: str,
    attribute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Not implemented yet (space_attribute_values)")


@router.post("/search", status_code=200)
def search_locations(
    payload: SearchLocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=501, detail="Not implemented yet (search attributes + buddies)")