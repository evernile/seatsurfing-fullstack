from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import get_current_user
from app.models import User

router = APIRouter(tags=["ui-compat"])

# ✅ Auth "optional" solo dove serve (evita loop se FE chiama senza token)
bearer_scheme = HTTPBearer(auto_error=False)


# ✅ La pagina Admin fa polling su questo: se torna 401/404 può andare in loop
@router.get("/booking/pendingapprovals/count")
def pending_approvals_count(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    # Se FE chiama prima di avere token -> NON deve esplodere
    if credentials is None:
        return 0

    # Se c'è token, possiamo anche semplicemente accettare e tornare 0 (stub)
    # (non cambiamo la tua auth attuale per non rompere niente)
    return 0


# Alcune dashboard chiamano /stats (nel Go si vede "stats/")
@router.get("/stats/")
@router.get("/stats")
def stats(current_user: User = Depends(get_current_user)):
    # Stub minimale
    return {}


# Nel Go screenshot si vede anche "uc/" (spesso = user count o usage count)
@router.get("/uc/")
@router.get("/uc")
def uc(current_user: User = Depends(get_current_user)) -> int:
    return 0