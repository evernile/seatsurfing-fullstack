from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt
import uuid

from app.core.database import get_db
from app.core.jwt import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed_password: str) -> bool:
    if not password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = None

    # 1) Authorization: Bearer <token>
    if credentials:
        token = credentials.credentials

    # 2) fallback cookie (se FE lo usa)
    if not token:
        token = request.cookies.get("accessToken")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

def require_org_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("org_admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Org admin required")
    return current_user

def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin required")
    return current_user