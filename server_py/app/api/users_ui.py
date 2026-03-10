from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/user", tags=["ui-compat"])

@router.get("/merge")
def merge_user(current_user: User = Depends(get_current_user)):
    # Stub compat: il frontend lo chiama, noi rispondiamo "ok"
    return {"ok": True}