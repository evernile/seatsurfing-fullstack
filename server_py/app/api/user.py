from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User

router = APIRouter(tags=["user"])

bearer_scheme = HTTPBearer(auto_error=False)


def _role_to_str(role_value) -> str:
    try:
        role_int = int(role_value)
    except Exception:
        return (role_value or "user").lower()

    mapping = {
        0: "user",
        10: "admin",
        20: "org_admin",
        21: "service_account_ro",
        22: "service_account_rw",
        90: "super_admin",
    }
    return mapping.get(role_int, "user")


def _role_to_int(role_str: str) -> int:
    role_str = (role_str or "user").lower()

    if role_str == "super_admin":
        return 90
    if role_str == "service_account_rw":
        return 22
    if role_str == "service_account_ro":
        return 21
    if role_str == "org_admin":
        return 20
    if role_str == "admin":
        return 10
    return 0


def _can_space_admin(user: User) -> bool:
    try:
        return int(getattr(user, "role", 0) or 0) >= 10
    except Exception:
        return False


def _can_org_admin(user: User) -> bool:
    try:
        return int(getattr(user, "role", 0) or 0) >= 20
    except Exception:
        return False


def _is_super_admin(user: User) -> bool:
    try:
        return int(getattr(user, "role", 0) or 0) >= 90
    except Exception:
        return False


def _organization_name_for_user(current_user: User) -> str:
    org_name = getattr(current_user, "organization_name", None)
    if org_name and str(org_name).strip():
        return str(org_name).strip()
    return "Sample Company"


def _me_payload(current_user: User) -> dict:
    role_str = _role_to_str(getattr(current_user, "role", 0))

    is_super_admin = role_str == "super_admin"
    is_org_admin = role_str in {"org_admin", "super_admin"}
    is_space_admin = role_str in {
        "admin",
        "org_admin",
        "super_admin",
        "service_account_ro",
        "service_account_rw",
    }

    require_password = bool((getattr(current_user, "hashed_password", "") or "").strip())

    firstname = (getattr(current_user, "firstname", "") or "").strip()
    lastname = (getattr(current_user, "lastname", "") or "").strip()

    org_id = getattr(current_user, "organization_id", None)
    org_id_str = str(org_id) if org_id else ""
    org_name = _organization_name_for_user(current_user)

    display_name = f"{firstname} {lastname}".strip() or current_user.email

    return {
        "id": str(current_user.id),
        "organization": {
            "id": org_id_str,
            "name": org_name,
            "firstname": "",
            "lastname": "",
            "email": "",
            "language": "",
            "country": "",
            "addressLine1": "",
            "addressLine2": "",
            "postalCode": "",
            "city": "",
            "vatId": "",
            "company": "",
        },
        "displayName": display_name,
        "requirePassword": require_password,
        "spaceAdmin": is_space_admin,
        "admin": is_org_admin,
        "orgAdmin": is_org_admin,
        "superAdmin": is_super_admin,
        "featureGroups": True,
        "cloudHosted": False,
        "pluginMenuItems": [],
        "email": current_user.email,
        "firstname": firstname,
        "lastname": lastname,
        "atlassianId": "",
        "role": _role_to_int(role_str),
        "authProviderId": "",
        "password": "",
        "organizationId": org_id_str,
    }


def _user_to_rest(u: User) -> dict:
    role_int = int(getattr(u, "role", 0) or 0)
    hashed_password = (getattr(u, "hashed_password", "") or "").strip()
    auth_provider_id = (getattr(u, "auth_provider_id", "") or "").strip()

    org_id = str(u.organization_id) if getattr(u, "organization_id", None) else ""
    org_name = getattr(u, "organization_name", None)
    if not org_name or not str(org_name).strip():
        org_name = "Sample Company"

    return {
        "id": str(u.id),
        "organization": {
            "id": org_id,
            "name": str(org_name),
        },
        "organizationId": org_id,
        "email": u.email,
        "firstname": (u.firstname or ""),
        "lastname": (u.lastname or ""),
        "atlassianId": "",
        "role": role_int,
        "spaceAdmin": role_int >= 10,
        "admin": role_int >= 20,
        "superAdmin": role_int >= 90,
        "requirePassword": bool(hashed_password),
        "authProviderId": auth_provider_id,
        "password": "",
    }


@router.get("/user/me", response_model=dict)
def me(current_user: User = Depends(get_current_user)):
    return _me_payload(current_user)


@router.get("/users/me", response_model=dict)
def me_alias(current_user: User = Depends(get_current_user)):
    return _me_payload(current_user)


@router.get("/user/merge", response_model=list)
def merge(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    return []


@router.get("/user/count", response_model=dict)
def user_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_org_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    count = (
        db.query(User)
        .filter(User.organization_id == current_user.organization_id)
        .count()
    )
    return {"count": count}


@router.get("/user/", response_model=list[dict])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _can_space_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    users = (
        db.query(User)
        .filter(User.organization_id == current_user.organization_id)
        .order_by(User.email.asc())
        .all()
    )

    return [_user_to_rest(u) for u in users]