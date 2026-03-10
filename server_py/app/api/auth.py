from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import create_access_token, decode_access_token
from app.core.security import verify_password
from app.models import Organization, User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# --------- Schemas ---------

class JWTResponse(BaseModel):
    accessToken: str
    refreshToken: str | None = None
    logoutUrl: str = ""
    profilePageUrl: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str
    organizationId: str


class RefreshRequest(BaseModel):
    refreshToken: str | None = None


class OrganizationOut(BaseModel):
    id: str
    name: str


class AuthProviderPublicResponse(BaseModel):
    id: str
    name: str


class AuthPreflightResponse(BaseModel):
    organization: OrganizationOut
    authProviders: list[AuthProviderPublicResponse] = []
    requirePassword: bool = False
    disablePasswordLogin: bool = False
    domain: str = ""


# --------- Helpers ---------

def _org_require_password(db: Session, org_id: str) -> bool:
    return (
        db.query(User)
        .filter(User.organization_id == org_id)
        .filter(User.hashed_password.isnot(None))
        .filter(User.hashed_password != "")
        .first()
        is not None
    )


def _resolve_org_from_domain(db: Session, domain: str) -> Organization | None:
    """
    FE chiama /auth/org/localhost.
    Non avendo una tabella domini, mapping semplice:
    - localhost/127.0.0.1 -> prova org 'seatsurfing'
    - altrimenti org.id == domain
    - fallback: se esiste una sola org -> usa quella
    """
    dom = (domain or "").strip().lower()

    if dom in {"localhost", "127.0.0.1"}:
        org = db.query(Organization).order_by(Organization.name.asc()).first()
        if org:
            return org

    org = db.query(Organization).filter(Organization.id == domain).first()
    if org:
        return org

    orgs = db.query(Organization).all()
    if len(orgs) == 1:
        return orgs[0]

    return None


# --------- Routes (parte OAuth non implementata) ---------

@router.get("/verify/{id}", response_model=JWTResponse)
def verify(id: str):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{id}/login/{type}/")
def login(id: str, type: str, redir: str | None = Query(default=None)):
    if type not in {"web", "app", "ui"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid login type")
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/{id}/callback")
def callback(id: str):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


# --------- Password login ---------

@router.post("/login", response_model=JWTResponse)
def login_password(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .filter(User.organization_id == payload.organizationId)
        .first()
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(str(user.id))

    # FE spesso pretende che refreshToken esista -> in dev riusiamo lo stesso token
    return JWTResponse(
        accessToken=access_token,
        refreshToken=access_token,
        logoutUrl="",
        profilePageUrl="",
    )


# --------- Refresh token (FIX CRITICO) ---------

@router.post("/refresh", response_model=JWTResponse)
def refresh_access_token(
    payload: RefreshRequest | None = None,
    request: Request = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """
    Seatsurfing FE spesso chiama /auth/refresh SENZA body.
    Quindi recuperiamo il token da:
    1. payload.refreshToken
    2. Authorization Bearer
    3. cookie accessToken
    """

    token = None

    if payload and payload.refreshToken:
        token = payload.refreshToken

    if not token and credentials:
        token = credentials.credentials

    if not token and request:
        token = request.cookies.get("accessToken")

    if not token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    data = decode_access_token(token)

    user_id = data.get("sub") or data.get("user_id") or data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = create_access_token(str(user_id))

    return JWTResponse(
        accessToken=new_access,
        refreshToken=token,
        logoutUrl="",
        profilePageUrl="",
    )


# --------- Preflight org ---------

@router.get("/singleorg", response_model=AuthPreflightResponse)
@router.get("/singleorg/", response_model=AuthPreflightResponse)
def single_org(db: Session = Depends(get_db)):
    orgs = db.query(Organization).all()
    if len(orgs) != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    org = orgs[0]
    return AuthPreflightResponse(
        organization=OrganizationOut(id=str(org.id), name=org.name),
        authProviders=[],
        requirePassword=_org_require_password(db, org.id),
        disablePasswordLogin=False,
        domain="",
    )


@router.get("/org/{domain}", response_model=AuthPreflightResponse)
@router.get("/org/{domain}/", response_model=AuthPreflightResponse)
def get_org_details(domain: str, db: Session = Depends(get_db)):
    org = _resolve_org_from_domain(db, domain)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return AuthPreflightResponse(
        organization=OrganizationOut(id=str(org.id), name=org.name),
        authProviders=[],
        requirePassword=_org_require_password(db, org.id),
        disablePasswordLogin=False,
        domain=domain,
    )