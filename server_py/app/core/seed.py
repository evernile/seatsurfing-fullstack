# app/core/seed.py

import os
import uuid

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Organization, User

# SETTINGS 
from app.repositories.settings_repository import get_settings_repository

USER_ROLE_USER = 0
USER_ROLE_SPACE_ADMIN = 10
USER_ROLE_ORG_ADMIN = 20
USER_ROLE_SUPER_ADMIN = 90

def _uuid_from_env(value: str) -> uuid.UUID:
    """
    Accetta:
    - UUID vero -> lo usa
    - stringa tipo "seatsurfing" -> genera UUID stabile (uuid5)
    """
    try:
        return uuid.UUID(value)
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, value)


def seed_db(db: Session) -> None:
    """
    Seed "safe" (attivabile solo con SEED_ENABLED=1)
    - crea (se manca) Organization con UUID stabile
    - crea/allinea admin user
    - crea tabella settings (se manca) + inserisce default settings per org
    """
    # HARD GUARD
    if os.getenv("SEED_ENABLED", "0") != "1":
        return

    org_id_raw = os.getenv("SEED_ORG_ID", "seatsurfing")
    org_name = os.getenv("SEED_ORG_NAME", "Seatsurfing")
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@seatsurfing.local")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "12345678")

    org_id = _uuid_from_env(org_id_raw)

    # 1) Organization
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        org = Organization(
            id=org_id,
            name=org_name,
            contact_firstname="",
            contact_lastname="",
            contact_email="",
            language="",
            signup_date=None,
            country="",
            address_line1="",
            address_line2="",
            postal_code="",
            city="",
            vat_id="",
            company="",
        )
        db.add(org)
        db.commit()
        db.refresh(org)
    else:
        
        if (org.name or "") != org_name:
            org.name = org_name
            db.commit()
            db.refresh(org)

    # 1b) Settings: ensure table + init default for org
   
    try:
        repo = get_settings_repository()
        repo.ensure_table(db)
        repo.init_default_settings_for_org(db, str(org.id))
        db.commit()
    except Exception:
        
        db.rollback()

    # 2) Admin user (solo se non esiste)
    user = db.query(User).filter(User.email == admin_email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=admin_email,
            full_name="Admin",
            organization_id=org.id,
            role=20,  # org_admin
            hashed_password=hash_password(admin_password),
        )
        db.add(user)
        db.commit()
        return

    
    changed = False

    if user.organization_id != org.id:
        user.organization_id = org.id
        changed = True

    
    try:
        current_role = int(user.role or 0)
    except Exception:
        current_role = 0

    if current_role != 20:
        user.role = 20
        changed = True

    if not getattr(user, "hashed_password", None):
        user.hashed_password = hash_password(admin_password)
        changed = True

    if changed:
        db.commit()