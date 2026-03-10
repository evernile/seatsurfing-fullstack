from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.models import AuthProvider


class AuthProviderRepository:
    def create(self, db: Session, e: AuthProvider) -> AuthProvider:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def get_one(self, db: Session, id: str) -> AuthProvider | None:
        return db.query(AuthProvider).filter(AuthProvider.id == id).first()

    def get_all(self, db: Session, organization_id: str) -> list[AuthProvider]:
        return (
            db.query(AuthProvider)
            .filter(AuthProvider.organization_id == organization_id)
            .order_by(AuthProvider.name.asc())
            .all()
        )

    def update(self, db: Session, e: AuthProvider) -> AuthProvider:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def delete(self, db: Session, id: str) -> None:
        db.query(AuthProvider).filter(AuthProvider.id == id).delete(synchronize_session=False)
        db.commit()

    def delete_all(self, db: Session, organization_id: str) -> None:
        db.query(AuthProvider).filter(AuthProvider.organization_id == organization_id).delete(
            synchronize_session=False
        )
        db.commit()


_auth_provider_repo: Optional[AuthProviderRepository] = None


def get_auth_provider_repository() -> AuthProviderRepository:
    global _auth_provider_repo
    if _auth_provider_repo is None:
        _auth_provider_repo = AuthProviderRepository()
    return _auth_provider_repo