from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/availability", tags=["ui-compat"])

# UI si aspetta una lista
@router.get("/")
def list_availability(current_user: User = Depends(get_current_user)):
    return []