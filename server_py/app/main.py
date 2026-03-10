import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.organizations import router as organizations_router
from app.api.spaces import router as spaces_router
from app.api.bookings import router as bookings_router
from app.api.locations import router as locations_router
from app.api.setting import router as setting_router
from app.api.locations_ui import router as locations_ui_router
from app.api.space_attributes_ui import router as space_attributes_ui_router
from app.api.users_ui import router as users_ui_router
from app.api.preferences_ui import router as preferences_ui_router
from app.api.buddies_ui import router as buddies_ui_router
from app.api.availability_ui import router as availability_ui_router
from app.api.booking_ui import router as booking_ui_router
from app.api.admin_ui import router as admin_ui_router
from app.api.check_update import router as check_update_router
from app.api.search import router as search_router
from app.api.user_preferences import router as user_preferences_router
from app.api.settings_ui import router as settings_ui_router
from app.api.groups_ui import router as groups_ui_router
from app.api.auth_provider import router as auth_provider_router

from app.core.database import SessionLocal
from app.core.seed import seed_db

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(users_ui_router)
app.include_router(organizations_router)
app.include_router(spaces_router)
app.include_router(bookings_router)
app.include_router(locations_router)
app.include_router(setting_router)
app.include_router(locations_ui_router)
app.include_router(space_attributes_ui_router)
app.include_router(preferences_ui_router)
app.include_router(buddies_ui_router)
app.include_router(availability_ui_router)
app.include_router(booking_ui_router)
app.include_router(admin_ui_router)
app.include_router(check_update_router)
app.include_router(search_router)
app.include_router(user_preferences_router)
app.include_router(settings_ui_router)
app.include_router(groups_ui_router)
app.include_router(auth_provider_router)



@app.on_event("startup")
def on_startup():
    # IMPORTANT: su DB Go originale NON seedare mai.
    # Lo abiliti solo se vuoi seedare un DB vuoto di sviluppo.
    if os.getenv("SEED_ENABLED", "0") != "1":
        return

    db = SessionLocal()
    try:
        seed_db(db)
    finally:
        db.close()

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}