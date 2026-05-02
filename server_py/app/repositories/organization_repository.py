from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import Organization, OrganizationDomain
from app.services.sample_data import create_sample_data


class OrganizationRepository:
    
    def get_one(self, db: Session, org_id: str) -> Organization | None:
        return db.query(Organization).filter(Organization.id == org_id).first()

    def get_by_email(self, db: Session, email: str) -> Organization | None:
        em = (email or "").lower()
        return (
            db.query(Organization)
            .filter(func.lower(Organization.contact_email) == em)
            .first()
        )

    def get_all(self, db: Session) -> list[Organization]:
        return db.query(Organization).order_by(Organization.name.asc()).all()

    def get_num_orgs(self, db: Session) -> int:
        return int(db.query(func.count(Organization.id)).scalar() or 0)

    def get_all_ids(self, db: Session) -> list[str]:
        rows = db.query(Organization.id).all()
        return [str(r[0]) for r in rows]

    def get_all_days_passed_since_signup(
        self,
        db: Session,
        days_passed: int,
        setting_exists: str = "",
    ) -> list[Organization]:
        """
        Go:
          WHERE (CURRENT_DATE::date - signup_date::date) = $1
          + opzionale NOT EXISTS su settings.name
        """
        
        q = db.query(Organization).filter(
            (func.current_date() - func.date(Organization.signup_date)) == int(days_passed)
        )

        if setting_exists:
            
            q = q.filter(
                text(
                    "NOT EXISTS ("
                    " SELECT 1 FROM settings s"
                    " WHERE s.organization_id = organizations.id"
                    "   AND s.name = :setting_name"
                    ")"
                )
            ).params(setting_name=setting_exists)

        return q.order_by(Organization.name.asc()).all()

    def create(self, db: Session, e: Organization, with_sample_data: bool = True) -> Organization:
        db.add(e)
        db.commit()
        db.refresh(e)

        if with_sample_data:
            create_sample_data(db, e.id)

        return e

    def update(self, db: Session, e: Organization) -> Organization:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def delete(self, db: Session, org_id: str) -> None:
        db.query(OrganizationDomain).filter(
            OrganizationDomain.organization_id == org_id
        ).delete(synchronize_session=False)

        db.query(Organization).filter(Organization.id == org_id).delete(
            synchronize_session=False
        )

        db.commit()

    
    def get_one_by_domain(self, db: Session, domain: str) -> Organization | None:
        dom = (domain or "").lower()
        return (
            db.query(Organization)
            .join(OrganizationDomain, Organization.id == OrganizationDomain.organization_id)
            .filter(func.lower(OrganizationDomain.domain) == dom)
            .filter(OrganizationDomain.active.is_(True))
            .first()
        )

    def get_domain(self, db: Session, org_id: str, domain: str) -> OrganizationDomain | None:
        dom = (domain or "").lower()
        return (
            db.query(OrganizationDomain)
            .filter(OrganizationDomain.organization_id == org_id)
            .filter(func.lower(OrganizationDomain.domain) == dom)
            .first()
        )

    def get_domains(self, db: Session, org_id: str) -> list[OrganizationDomain]:
        return (
            db.query(OrganizationDomain)
            .filter(OrganizationDomain.organization_id == org_id)
            .order_by(OrganizationDomain.domain.asc())
            .all()
        )

    def get_all_domains(self, db: Session) -> list[OrganizationDomain]:
        return db.query(OrganizationDomain).order_by(OrganizationDomain.domain.asc()).all()

    def add_domain(
        self,
        db: Session,
        org_id: str,
        domain: str,
        active: bool,
        verify_token: str | None = None,
    ) -> OrganizationDomain:
        d = OrganizationDomain(
            domain=(domain or "").lower(),
            organization_id=org_id,
            active=bool(active),
            verify_token=verify_token,
            primary_domain=False,
            accessible=False,
            access_check=None,
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        return d

    def remove_domain(self, db: Session, org_id: str, domain: str) -> None:
        dom = (domain or "").lower()
        db.query(OrganizationDomain).filter(
            OrganizationDomain.organization_id == org_id,
            func.lower(OrganizationDomain.domain) == dom,
        ).delete(synchronize_session=False)
        db.commit()

    def activate_domain(self, db: Session, org_id: str, domain: str) -> None:
        dom = (domain or "").lower()
        db.query(OrganizationDomain).filter(
            OrganizationDomain.organization_id == org_id,
            func.lower(OrganizationDomain.domain) == dom,
        ).update({"active": True}, synchronize_session=False)
        db.commit()

    def set_domain_accessibility(
        self,
        db: Session,
        org_id: str,
        domain: str,
        accessible: bool,
        access_check: datetime,
    ) -> None:
        dom = (domain or "").lower()
        db.query(OrganizationDomain).filter(
            OrganizationDomain.organization_id == org_id,
            func.lower(OrganizationDomain.domain) == dom,
        ).update(
            {"accessible": bool(accessible), "access_check": access_check},
            synchronize_session=False,
        )
        db.commit()

    def set_primary_domain(self, db: Session, org_id: str, domain: str) -> None:
        dom = (domain or "").lower()

        db.query(OrganizationDomain).filter(
            OrganizationDomain.organization_id == org_id
        ).update({"primary_domain": False}, synchronize_session=False)

        db.query(OrganizationDomain).filter(
            OrganizationDomain.organization_id == org_id,
            func.lower(OrganizationDomain.domain) == dom,
        ).update({"primary_domain": True}, synchronize_session=False)

        db.commit()

    def get_primary_domain(self, db: Session, org_id: str) -> OrganizationDomain | None:
        domains = self.get_domains(db, org_id)

        for d in domains:
            if bool(d.active) and bool(getattr(d, "primary_domain", False)):
                return d

        for d in domains:
            if bool(d.active):
                return d

        return None