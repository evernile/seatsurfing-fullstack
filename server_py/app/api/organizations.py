from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Organization, User
from app.schemas.organization import OrganizationCreate, OrganizationOut

router = APIRouter(tags=["organizations"])


class OrganizationUpdateRequest(BaseModel):
    name: str
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    language: str = ""
    country: str = ""
    addressLine1: str = ""
    addressLine2: str = ""
    postalCode: str = ""
    city: str = ""
    vatId: str = ""
    company: str = ""


def _org_to_detail_payload(org: Organization) -> dict:
    return {
        "id": str(org.id),
        "name": org.name or "",
        "firstname": getattr(org, "contact_firstname", "") or "",
        "lastname": getattr(org, "contact_lastname", "") or "",
        "email": getattr(org, "contact_email", "") or "",
        "language": getattr(org, "language", "") or "",
        "signupDate": None,
        "country": getattr(org, "country", "") or "",
        "addressLine1": getattr(org, "address_line1", "") or "",
        "addressLine2": getattr(org, "address_line2", "") or "",
        "postalCode": getattr(org, "postal_code", "") or "",
        "city": getattr(org, "city", "") or "",
        "vatId": getattr(org, "vat_id", "") or "",
        "company": getattr(org, "company", "") or "",
    }


def _available_countries() -> dict:
    try:
        import pycountry  # type: ignore

        eu_codes = {
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE",
            "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT",
            "RO", "SK", "SI", "ES", "SE",
        }

        eu: dict[str, str] = {}
        other: dict[str, str] = {}

        for country in pycountry.countries:
            code = getattr(country, "alpha_2", None)
            name = getattr(country, "name", None)
            if not code or not name:
                continue

            if code in eu_codes:
                eu[code] = name
            else:
                other[code] = name

        return {
            "EU": dict(sorted(eu.items())),
            "Other": dict(sorted(other.items())),
        }
    except Exception:
        return {
            "EU": {
                "AT": "Austria",
                "BE": "Belgium",
                "BG": "Bulgaria",
                "HR": "Croatia",
                "CY": "Cyprus",
                "CZ": "Czech Republic",
                "DK": "Denmark",
                "EE": "Estonia",
                "FI": "Finland",
                "FR": "France",
                "DE": "Germany",
                "GR": "Greece",
                "HU": "Hungary",
                "IE": "Ireland",
                "IT": "Italy",
                "LV": "Latvia",
                "LT": "Lithuania",
                "LU": "Luxembourg",
                "MT": "Malta",
                "NL": "Netherlands",
                "PL": "Poland",
                "PT": "Portugal",
                "RO": "Romania",
                "SK": "Slovakia",
                "SI": "Slovenia",
                "ES": "Spain",
                "SE": "Sweden",
            },
            "Other": {
                "CH": "Switzerland",
                "GB": "United Kingdom",
                "NO": "Norway",
                "US": "United States",
                "CA": "Canada",
                "AU": "Australia",
            },
        }


@router.get("/organization/country")
def get_available_countries(current_user: User = Depends(get_current_user)):
    return _available_countries()


@router.post("/organizations", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_org(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(Organization).filter(Organization.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Organization already exists")

    org = Organization(
        id=payload.id,
        name=payload.name,
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    return OrganizationOut(id=org.id, name=org.name)


@router.get("/organizations/me", response_model=OrganizationOut)
def get_my_org(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="User has no organization")

    org = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationOut(id=org.id, name=org.name)


@router.get("/organizations/{org_id}", response_model=OrganizationOut)
def get_org_plural(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return OrganizationOut(id=org.id, name=org.name)


@router.get("/organization/{org_id}")
def get_org_singular(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return _org_to_detail_payload(org)


@router.put("/organization/{org_id}")
def update_org_singular(
    org_id: str,
    payload: OrganizationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.name = payload.name
    setattr(org, "contact_firstname", payload.firstname or "")
    setattr(org, "contact_lastname", payload.lastname or "")
    setattr(org, "contact_email", payload.email or "")
    setattr(org, "language", payload.language or "")
    setattr(org, "country", payload.country or "")
    setattr(org, "address_line1", payload.addressLine1 or "")
    setattr(org, "address_line2", payload.addressLine2 or "")
    setattr(org, "postal_code", payload.postalCode or "")
    setattr(org, "city", payload.city or "")
    setattr(org, "vat_id", payload.vatId or "")
    setattr(org, "company", payload.company or "")

    db.commit()
    db.refresh(org)

    return {"verifyUuid": ""}


@router.get("/organization/{org_id}/domain")
@router.get("/organization/{org_id}/domain/")
def get_org_domains(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return [
        {
            "domain": "localhost:3000",
            "active": True,
            "verifyToken": "",
            "primary": True,
            "accessible": True,
            "accessCheck": None,
        }
    ]


@router.get("/organization/{org_id}/domain/primary")
def get_org_primary_domain(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "domain": "localhost:3000",
        "active": True,
        "verifyToken": "",
        "primary": True,
        "accessible": True,
        "accessCheck": None,
    }