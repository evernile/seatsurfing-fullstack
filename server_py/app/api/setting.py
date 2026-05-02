from zoneinfo import available_timezones

from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/setting", tags=["setting"])


def _settings_list():
    return [
        {"name": "install_id", "value": "d220f75c-6cb5-442d-8c3f-27755063188c"},
        {"name": "db_version", "value": "32"},

        {"name": "allow_any_user", "value": "1"},
        {"name": "confluence_server_shared_secret", "value": ""},
        {"name": "confluence_anonymous", "value": "0"},

        {"name": "max_bookings_per_user", "value": "10"},
        {"name": "max_concurrent_bookings_per_user", "value": "0"},
        {"name": "max_days_in_advance", "value": "14"},

        # Booking retention (Delete booking data older than ...)
        {"name": "booking_retention_enabled", "value": "0"},
        {"name": "booking_retention_days", "value": "365"},

        # Cancel booking before start
        {"name": "enable_max_hours_before_delete", "value": "0"},
        {"name": "max_hours_before_delete", "value": "0"},

        {"name": "min_booking_duration_hours", "value": "0"},
        {"name": "max_booking_duration_hours", "value": "12"},

        {"name": "max_hours_partially_booked_enabled", "value": "0"},
        {"name": "max_hours_partially_booked", "value": "8"},

        {"name": "daily_basis_booking", "value": "0"},
        {"name": "no_admin_restrictions", "value": "0"},
        {"name": "custom_logo_url", "value": ""},
        {"name": "show_names", "value": "0"},
        {"name": "allow_booking_nonexist_users", "value": "0"},
        {"name": "disable_buddies", "value": "0"},
        {"name": "default_timezone", "value": "Europe/Berlin"},
        {"name": "allow_recurring_bookings", "value": "1"},
        {"name": "subject_default", "value": "2"},

        {"name": "feature_no_user_limit", "value": "0"},
        {"name": "feature_custom_domains", "value": "1"},
        {"name": "feature_groups", "value": "1"},
        {"name": "feature_auth_providers", "value": "1"},
        {"name": "feature_recurring_bookings", "value": "1"},

        # compat / UI
        {"name": "cloud_hosted", "value": "0"},
        {"name": "subscription_active", "value": "1"},
        {"name": "_sys_org_primary_domain", "value": ""},
        {"name": "_sys_disable_password_login", "value": "0"},
        {"name": "_sys_admin_menu_items", "value": "[]"},
        {"name": "_sys_admin_welcome_screens", "value": "[]"},
    ]


@router.get("/timezones")
def get_timezones(current_user: User = Depends(get_current_user)):
    return sorted(list(available_timezones()))


@router.get("/")
@router.get("")
def get_settings(current_user: User = Depends(get_current_user)):
    return _settings_list()


@router.get("/{name}")
def get_setting(name: str, current_user: User = Depends(get_current_user)):
    for item in _settings_list():
        if item["name"] == name:
            return item
    return {"name": name, "value": ""}