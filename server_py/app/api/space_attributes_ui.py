from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/space-attribute", tags=["ui-compat"])

@router.get("/")
def list_space_attributes(current_user: User = Depends(get_current_user)):
    # Stub: nessun attributo
    return []