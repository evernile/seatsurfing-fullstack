import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, Group
from app.repositories.group_repository import GroupRepository

router = APIRouter(prefix="/groups", tags=["groups"])
repo = GroupRepository()

def can_access_org(user: User, org_id: str) -> bool:
    return bool(user.organization_id) and user.organization_id == org_id

def can_admin_org(user: User, org_id: str) -> bool:
    return can_access_org(user, org_id) and user.role == "admin"

def can_space_admin_org(user: User, org_id: str) -> bool:
    return can_access_org(user, org_id) and user.role == "admin"  # se hai ruolo "space_admin" cambialo qui

@router.get("/")
def get_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not can_space_admin_org(current_user, current_user.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return repo.get_all(db, current_user.organization_id)

@router.get("/{group_id}")
def get_one(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = repo.get_one(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if not can_space_admin_org(current_user, g.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return g

@router.post("/", status_code=201)
def create(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not can_admin_org(current_user, current_user.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")
    name = (payload.get("name") or "").strip()
    if len(name) < 3:
        raise HTTPException(status_code=400, detail="Invalid name")

    g = Group(organization_id=current_user.organization_id, name=name)
    g = repo.create(db, g)
    return {"id": str(g.id)}

@router.put("/{group_id}")
def update(
    group_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = repo.get_one(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if not can_admin_org(current_user, g.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    name = (payload.get("name") or "").strip()
    if len(name) < 3:
        raise HTTPException(status_code=400, detail="Invalid name")

    g.name = name
    repo.update(db, g)
    return {"status": "updated"}

@router.delete("/{group_id}")
def delete(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = repo.get_one(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if not can_admin_org(current_user, g.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    repo.delete(db, g)
    return {"status": "updated"}

@router.get("/{group_id}/member")
def get_members(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = repo.get_one(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if not can_admin_org(current_user, g.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    return repo.get_member_user_ids(db, group_id)

@router.put("/{group_id}/member")
def add_members(
    group_id: str,
    members: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = repo.get_one(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if not can_admin_org(current_user, g.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # valida UUID
    for m in members:
        try:
            uuid.UUID(m)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid member id")

    repo.add_members(db, group_id, members)
    return {"status": "updated"}

@router.post("/{group_id}/member/remove")
def remove_members(
    group_id: str,
    members: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    g = repo.get_one(db, group_id)
    if not g:
        raise HTTPException(status_code=404, detail="Not found")
    if not can_admin_org(current_user, g.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    repo.remove_members(db, group_id, members)
    return {"status": "updated"}