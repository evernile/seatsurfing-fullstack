from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/setting", tags=["setting"])


@router.get("/")
def get_settings(current_user: User = Depends(get_current_user)):
    return [
        {"name": "max_bookings_per_user", "value": "10"},
        {"name": "max_concurrent_bookings_per_user", "value": "0"},
        {"name": "max_days_in_advance", "value": "14"},
        {"name": "max_booking_duration_hours", "value": "12"},
        {"name": "max_hours_before_delete", "value": "0"},
        {"name": "min_booking_duration_hours", "value": "0"},
        {"name": "daily_basis_booking", "value": "0"},
        {"name": "no_admin_restrictions", "value": "0"},
        {"name": "max_hours_partially_booked", "value": "8"},
        {"name": "max_hours_partially_booked_enabled", "value": "0"},
        {"name": "show_names", "value": "1"},
        {"name": "disable_buddies", "value": "1"},
        {"name": "custom_logo_url", "value": ""},
        {"name": "default_timezone", "value": "Europe/Rome"},
        {"name": "feature_recurring_bookings", "value": "1"},
        {"name": "allow_recurring_bookings", "value": "1"},
        {"name": "_sys_admin_menu_items", "value": "[]"},
        {"name": "_sys_admin_welcome_screens", "value": "[]"},
        {"name": "feature_groups", "value": "1"},
        {"name": "feature_auth_providers", "value": "1"},
        {"name": "cloud_hosted", "value": "0"},
        {"name": "subscription_active", "value": "1"},
        {"name": "_sys_org_primary_domain", "value": ""},
        {"name": "_sys_disable_password_login", "value": "0"},
        {"name": "subject_default", "value": "2"},
    ]