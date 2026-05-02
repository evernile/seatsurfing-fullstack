from __future__ import annotations

import urllib.parse
import requests

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import create_access_token, decode_access_token
from app.core.security import verify_password
from app.models import AuthProvider, Organization, OrganizationDomain, User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# Schemas

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


# HELPERS

def _org_require_password(db: Session, org_id: str) -> bool:
    return (
        db.query(User)
        .filter(User.organization_id == org_id)
        .filter(User.hashed_password.isnot(None))
        .filter(User.hashed_password != "")
        .first()
        is not None
    )


def _public_auth_providers_for_org(db: Session, org_id: str):
    providers = (
        db.query(AuthProvider)
        .filter(AuthProvider.organization_id == org_id)
        .all()
    )

    return [
        AuthProviderPublicResponse(
            id=str(p.id),
            name=p.name
        )
        for p in providers
    ]


def _resolve_org_from_domain(db: Session, domain: str) -> Organization | None:
    dom = (domain or "").strip().lower()

    localhost_aliases = {
        "localhost",
        "127.0.0.1",
        "localhost:3000",
        "127.0.0.1:3000",
        "localhost:8000",
        "127.0.0.1:8000",
        "localhost:8080",
        "127.0.0.1:8080",
        "localhost:5173",
        "127.0.0.1:5173",
    }

    if dom in localhost_aliases:
        org = db.query(Organization).first()
        if org:
            return org

    
    org_domain = (
        db.query(OrganizationDomain)
        .filter(OrganizationDomain.domain == dom)
        .first()
    )

    if org_domain:
        return db.query(Organization).filter(
            Organization.id == org_domain.organization_id
        ).first()

    # fallback
    orgs = db.query(Organization).all()
    if len(orgs) == 1:
        return orgs[0]

    return None


# ROUTES

@router.get("/verify/{id}", response_model=JWTResponse)
def verify(id: str):
    raise HTTPException(status_code=501, detail="Not implemented")


# LOGIN MICROSOFT
@router.get("/{id}/login/{type}/")
def login(
    id: str,
    type: str,
    redir: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    provider = db.query(AuthProvider).filter(AuthProvider.id == id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    redirect_uri = f"http://localhost:8000/auth/{id}/callback"

    params = {
        "client_id": provider.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": provider.scopes,
        "state": "xyz"
    }

    url = provider.auth_url + "?" + urllib.parse.urlencode(params)

    return RedirectResponse(url)


# CALLBACK MICROSOFT
@router.get("/{id}/callback")
def callback(id: str, code: str, db: Session = Depends(get_db)):
    provider = db.query(AuthProvider).filter(AuthProvider.id == id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    redirect_uri = f"http://localhost:8000/auth/{id}/callback"

    # scambio code → token
    token_res = requests.post(
        provider.token_url,
        data={
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )

    token_data = token_res.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Token error")

    # prendi dati utente
    userinfo_res = requests.get(
        provider.userinfo_url,
        headers={"Authorization": f"Bearer {access_token}"}
    )

    userinfo = userinfo_res.json()

    email = userinfo.get(provider.userinfo_email_field)
    firstname = userinfo.get(provider.userinfo_firstname_field, "")
    lastname = userinfo.get(provider.userinfo_lastname_field, "")

    if not email:
        raise HTTPException(status_code=400, detail="Email missing")

    # crea utente se non esiste
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            email=email,
            firstname=firstname,
            lastname=lastname,
            organization_id=provider.organization_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    jwt_token = create_access_token(str(user.id))

    # redirect UI
    return RedirectResponse(f"http://localhost:3000/?token={jwt_token}")


# PASSWORD LOGIN 

@router.post("/login", response_model=JWTResponse)
def login_password(payload: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == payload.email)
        .filter(User.organization_id == payload.organizationId)
        .first()
    )

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(str(user.id))

    return JWTResponse(
        accessToken=access_token,
        refreshToken=access_token,
        logoutUrl="",
        profilePageUrl="",
    )


# REFRESH TOKEN

@router.post("/refresh", response_model=JWTResponse)
def refresh_access_token(
    request: Request,
    payload: RefreshRequest | None = None,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    token = None

    if payload and payload.refreshToken:
        token = payload.refreshToken

    if not token and credentials:
        token = credentials.credentials

    if not token:
        token = request.cookies.get("accessToken")

    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    data = decode_access_token(token)
    user_id = data.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    new_token = create_access_token(str(user_id))

    return JWTResponse(
        accessToken=new_token,
        refreshToken=token,
        logoutUrl="",
        profilePageUrl="",
    )


# ORG PREFLIGHT

@router.get("/org/{domain}", response_model=AuthPreflightResponse)
def get_org(domain: str, db: Session = Depends(get_db)):
    org = _resolve_org_from_domain(db, domain)

    if not org:
        raise HTTPException(status_code=404, detail="Not found")

    return AuthPreflightResponse(
        organization=OrganizationOut(id=str(org.id), name=org.name),
        authProviders=_public_auth_providers_for_org(db, str(org.id)),
        requirePassword=_org_require_password(db, str(org.id)),
        disablePasswordLogin=False,
        domain=domain,
    )