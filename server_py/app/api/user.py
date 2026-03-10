from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import get_current_user
from app.models import User

router = APIRouter(tags=["user"])

bearer_scheme = HTTPBearer(auto_error=False)


def _role_to_str(role_value) -> str:
    """
    Mapping coerente con il backend Go:
    0  = user
    10 = space admin
    20 = org admin
    21 = service account ro
    22 = service account rw
    90 = super admin
    """
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

    return {
        "id": str(current_user.id),
        "organization": {
            "id": org_id_str,
            "name": "",
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


@router.get("/user/me", response_model=dict)
def me(current_user: User = Depends(get_current_user)):
    return _me_payload(current_user)


@router.get("/users/me", response_model=dict)
def me_alias(current_user: User = Depends(get_current_user)):
    return _me_payload(current_user)


@router.get("/user/merge", response_model=list)
def merge(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    return []


from sqlalchemy.orm import Session
from app.core.database import get_db


@router.get("/user/", response_model=list[dict])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id

    users = (
        db.query(User)
        .filter(User.organization_id == org_id)
        .order_by(User.email.asc())
        .all()
    )

    result = []

    for u in users:
        result.append({
            "id": str(u.id),
            "email": u.email,
            "firstname": (u.firstname or ""),
            "lastname": (u.lastname or ""),
            "organizationId": str(u.organization_id) if u.organization_id else "",
            "role": u.role,
            "spaceAdmin": u.role >= 10,
            "admin": u.role >= 20,
            "superAdmin": u.role >= 90,
        })

    return result