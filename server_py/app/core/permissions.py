from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.models import User


def require_org_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("org_admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Org admin required",
        )
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin required",
        )
    return current_user


def require_same_user_or_admin(
    target_user_id: int,
    current_user: User,
) -> None:
    
    if current_user.role in ("org_admin", "super_admin"):
        return
    if current_user.id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed",
        )