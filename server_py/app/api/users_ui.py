from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/user", tags=["ui-compat"])


@router.get("/merge")
def merge_user(current_user: User = Depends(get_current_user)):
    return {"ok": True}


@router.get("/count")
def count_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(User)
        .filter(User.organization_id == current_user.organization_id)
        .count()
    )
    return {"count": count}