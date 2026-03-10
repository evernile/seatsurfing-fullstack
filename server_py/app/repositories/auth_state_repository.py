from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import AuthState


class AuthStateRepository:
    def create(self, db: Session, e: AuthState) -> AuthState:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def get_one(self, db: Session, id: str) -> AuthState | None:
        return db.query(AuthState).filter(AuthState.id == id).first()

    def delete(self, db: Session, id: str) -> None:
        db.query(AuthState).filter(AuthState.id == id).delete(synchronize_session=False)
        db.commit()

    def delete_expired(self, db: Session) -> None:
        now = datetime.utcnow()
        db.query(AuthState).filter(AuthState.expiry < now).delete(synchronize_session=False)
        db.commit()

    def get_by_auth_provider_id(self, db: Session, auth_provider_id: str) -> list[AuthState]:
        return db.query(AuthState).filter(AuthState.auth_provider_id == auth_provider_id).all()


_auth_state_repo: Optional[AuthStateRepository] = None


def get_auth_state_repository() -> AuthStateRepository:
    global _auth_state_repo
    if _auth_state_repo is None:
        _auth_state_repo = AuthStateRepository()
    return _auth_state_repo