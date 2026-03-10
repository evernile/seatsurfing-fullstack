from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Organization, User
from app.schemas.organization import OrganizationCreate, OrganizationOut

router = APIRouter(tags=["organizations"])


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

    return {
        "id": str(org.id),
        "name": org.name or "",
        "contactFirstname": getattr(org, "contact_firstname", "") or "",
        "contactLastname": getattr(org, "contact_lastname", "") or "",
        "contactEmail": getattr(org, "contact_email", "") or "",
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

    
    return []


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
        "domain": "",
        "organizationId": str(org.id),
        "active": False,
        "verifyToken": "",
        "primary": False,
        "accessible": False,
        "accessCheck": None,
    }