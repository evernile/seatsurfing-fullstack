from fastapi import APIRouter

router = APIRouter(tags=["default"])


@router.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
