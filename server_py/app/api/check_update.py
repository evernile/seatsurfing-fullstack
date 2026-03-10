from fastapi import APIRouter

router = APIRouter(prefix="/check-update", tags=["ui-compat"])


@router.get("/")
@router.get("")
def check_update():
    """
    Porting di check-update-router.go

    In Go:
    - Se Latest == nil -> 404
    - Altrimenti -> JSON latest

    In Python:
    Per evitare problemi FE, restituiamo sempre 200.
    Se non hai un sistema di update reale, ritorniamo {}.
    """

    # Se vuoi simulare una versione disponibile:
    # return {
    #     "version": "1.6.1",
    #     "url": "https://github.com/seatsurfing/seatsurfing/releases",
    # }

    # Versione safe: nessun update disponibile
    return {}