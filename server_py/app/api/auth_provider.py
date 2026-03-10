from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import AuthProvider, User

router = APIRouter(prefix="/auth-provider", tags=["auth-provider"])


def _to_payload(p: AuthProvider) -> dict:
    return {
        "id": str(p.id),
        "organizationId": str(p.organization_id),
        "name": p.name or "",
        "providerType": p.provider_type,
        "authUrl": p.auth_url or "",
        "tokenUrl": p.token_url or "",
        "authStyle": p.auth_style,
        "scopes": p.scopes or "",
        "userInfoUrl": p.userinfo_url or "",
        "userInfoEmailField": p.userinfo_email_field or "",
        "userInfoFirstnameField": p.userinfo_firstname_field or "",
        "userInfoLastnameField": p.userinfo_lastname_field or "",
        "clientId": p.client_id or "",
        "clientSecret": p.client_secret or "",
        "logoutUrl": p.logout_url or "",
        "profilePageUrl": p.profile_page_url or "",
        "readOnly": bool(p.read_only),
    }


@router.get("/", response_model=list[dict])
def get_auth_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org_id = current_user.organization_id
    providers = (
        db.query(AuthProvider)
        .filter(AuthProvider.organization_id == org_id)
        .order_by(AuthProvider.name.asc())
        .all()
    )
    return [_to_payload(p) for p in providers]