from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import get_current_user
from app.models import User

router = APIRouter(tags=["ui-compat"])


bearer_scheme = HTTPBearer(auto_error=False)


@router.get("/booking/pendingapprovals/count")
def pending_approvals_count(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    
    if credentials is None:
        return 0

    
    return 0


@router.get("/stats/")
@router.get("/stats")
def stats(current_user: User = Depends(get_current_user)):
    # Stub minimale
    return {}


@router.get("/uc/")
@router.get("/uc")
def uc(current_user: User = Depends(get_current_user)) -> int:
    return 0