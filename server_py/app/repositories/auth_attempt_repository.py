from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.models import AuthAttempt, User


class AuthAttemptRepository:
    def create(self, db: Session, e: AuthAttempt) -> AuthAttempt:
        db.add(e)
        db.commit()
        db.refresh(e)
        return e

    def record_login_attempt(self, db: Session, user: User, success: bool) -> AuthAttempt:
        e = AuthAttempt(
            user_id=user.id,
            email=user.email,
            timestamp=datetime.utcnow(),
            successful=bool(success),
        )
        e = self.create(db, e)
        self._check_ban_user(db, user)
        return e

    def _check_ban_user(self, db: Session, user: User) -> None:
        """
        Porting 1:1 della logica Go.
        Dipende da config: LoginProtectionSlidingWindowSeconds, LoginProtectionMaxFails, LoginProtectionBanMinutes.
        Se non ce l’hai ancora in Python config, metti default qui (poi li colleghi al tuo config).
        """
        # --- DEFAULTS (puoi agganciarli al tuo config quando vuoi) ---
        sliding_window_seconds = 300
        max_fails = 5
        ban_minutes = 15
        # -----------------------------------------------------------

        # last successful login timestamp (fallback epoch)
        last_success = (
            db.query(AuthAttempt.timestamp)
            .filter(AuthAttempt.user_id == user.id)
            .filter(AuthAttempt.successful.is_(True))
            .order_by(AuthAttempt.timestamp.desc())
            .limit(1)
            .scalar()
        )
        if not last_success:
            last_success = datetime.fromtimestamp(0)

        limit = datetime.utcnow() - timedelta(seconds=sliding_window_seconds)

        # Go query:
        # COUNT where user_id=$1 AND timestamp > limit AND timestamp > lastSuccessfulLogin
        num_failed = (
            db.query(AuthAttempt)
            .filter(AuthAttempt.user_id == user.id)
            .filter(AuthAttempt.timestamp > limit)
            .filter(AuthAttempt.timestamp > last_success)
            .count()
        )

        if num_failed >= max_fails:
            ban_expiry = datetime.utcnow() + timedelta(minutes=ban_minutes)
            user.disabled = True
            user.ban_expiry = ban_expiry
            db.add(user)
            db.commit()


_auth_attempt_repo: Optional[AuthAttemptRepository] = None


def get_auth_attempt_repository() -> AuthAttemptRepository:
    global _auth_attempt_repo
    if _auth_attempt_repo is None:
        _auth_attempt_repo = AuthAttemptRepository()
    return _auth_attempt_repo