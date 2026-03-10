from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/group", tags=["ui-compat"])

@router.get("/")
def list_groups(current_user: User = Depends(get_current_user)):
    return []