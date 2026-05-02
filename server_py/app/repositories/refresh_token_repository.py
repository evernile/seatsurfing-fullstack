from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session

from app.models import RefreshToken, User


class RefreshTokenRepository:
    

    def create(self, db: Session, e: RefreshToken) -> RefreshToken:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def get_one(self, db: Session, token_id: str) -> RefreshToken | None:
        return db.query(RefreshToken).filter(RefreshToken.id == token_id).first()

    def delete(self, db: Session, e: RefreshToken) -> None:
        db.delete(e)
        db.commit()

    def delete_expired(self, db: Session) -> int:
        now = datetime.utcnow()
        q = db.query(RefreshToken).filter(RefreshToken.expiry < now)
        deleted = q.delete(synchronize_session=False)
        db.commit()
        return deleted

    def delete_of_user(self, db: Session, u: User) -> int:
        q = db.query(RefreshToken).filter(RefreshToken.user_id == u.id)
        deleted = q.delete(synchronize_session=False)
        db.commit()
        return deleted


_refresh_token_repository: RefreshTokenRepository | None = None


def get_refresh_token_repository() -> RefreshTokenRepository:
    global _refresh_token_repository
    if _refresh_token_repository is None:
        _refresh_token_repository = RefreshTokenRepository()
    return _refresh_token_repository