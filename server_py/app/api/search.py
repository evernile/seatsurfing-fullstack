from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Location, Space, Group  

router = APIRouter(prefix="/search", tags=["ui-compat"])


# --- permessi "compat" ---
def _can_space_admin_org(user: User) -> bool:
    
    return getattr(user, "role", None) in ("admin", "org_admin", "super_admin")


def _can_admin_org(user: User) -> bool:
   
    return getattr(user, "role", None) in ("admin", "org_admin", "super_admin")


def _like(q: str) -> str:
    q = (q or "").strip()
    return f"%{q}%"


@router.get("/")
def get_results(
    query: str | None = Query(default="", alias="query"),
    includeUsers: str | None = Query(default="0"),
    includeGroups: str | None = Query(default="0"),
    includeLocations: str | None = Query(default="0"),
    includeSpaces: str | None = Query(default="0"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --- auth/permessi ---
    if not _can_space_admin_org(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    keyword = (query or "").strip()
    like = _like(keyword)

    res = {
        "users": [],
        "locations": [],
        "spaces": [],
        "groups": [],
    }

    # ---- USERS ----
    if includeUsers == "1" and _can_admin_org(current_user):
       
        q = db.query(User).filter(User.organization_id == current_user.organization_id)

        
        conditions = [User.email.ilike(like)]
        if hasattr(User, "firstname"):
            conditions.append(getattr(User, "firstname").ilike(like))
        if hasattr(User, "lastname"):
            conditions.append(getattr(User, "lastname").ilike(like))
        if hasattr(User, "full_name"):
            conditions.append(getattr(User, "full_name").ilike(like))

        if keyword:
            q = q.filter(or_(*conditions))

        users = q.limit(50).all()

        for u in users:
            res["users"].append(
                {
                    "id": str(u.id),
                    "email": getattr(u, "email", "") or "",
                    "firstname": getattr(u, "firstname", "") or "",
                    "lastname": getattr(u, "lastname", "") or "",
                    "role": getattr(u, "role", "") or "",
                    "organizationId": getattr(u, "organization_id", "") or "",
                    "admin": getattr(u, "role", None) in ("admin", "org_admin", "super_admin"),
                    "spaceAdmin": getattr(u, "role", None) in ("admin", "org_admin", "super_admin"),
                    "superAdmin": getattr(u, "role", None) == "super_admin",
                }
            )

    # ---- GROUPS ----
    if includeGroups == "1":
        
        q = db.query(Group).filter(Group.organization_id == current_user.organization_id)
        if keyword and hasattr(Group, "name"):
            q = q.filter(getattr(Group, "name").ilike(like))

        groups = q.limit(50).all()
        for g in groups:
            res["groups"].append(
                {
                    "id": str(getattr(g, "id")),
                    "name": getattr(g, "name", "") or "",
                }
            )

    # ---- LOCATIONS ----
    if includeLocations == "1":
        
        q = db.query(Location).filter(Location.organization_id == current_user.organization_id)
        if keyword and hasattr(Location, "name"):
            q = q.filter(getattr(Location, "name").ilike(like))

        locs = q.limit(50).all()
        for l in locs:
            res["locations"].append(
                {
                    "id": str(getattr(l, "id")),
                    "name": getattr(l, "name", "") or "",
                    "timezone": getattr(l, "tz", None) or getattr(l, "timezone", "") or "Europe/Rome",
                    "enabled": bool(getattr(l, "enabled", True)),
                }
            )

    # ---- SPACES ----
    if includeSpaces == "1":
        
        q = db.query(Space).filter(Space.organization_id == current_user.organization_id)

        
        conditions = []
        if hasattr(Space, "name"):
            conditions.append(getattr(Space, "name").ilike(like))
        if hasattr(Space, "label"):
            conditions.append(getattr(Space, "label").ilike(like))
        if hasattr(Space, "code"):
            conditions.append(getattr(Space, "code").ilike(like))

        if keyword and conditions:
            q = q.filter(or_(*conditions))

        spaces = q.limit(50).all()
        for s in spaces:
            res["spaces"].append(
                {
                    "id": str(getattr(s, "id")),
                    "name": getattr(s, "name", "") or getattr(s, "label", "") or "",
                    "locationId": str(getattr(s, "location_id", "")) if getattr(s, "location_id", None) is not None else "",
                    "enabled": bool(getattr(s, "enabled", True)),
                }
            )

    return res