from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache import get_cache


class SettingType(str, Enum):
    string = "string"
    int = "int"
    bool = "bool"


@dataclass(frozen=True)
class SettingName:
    name: str
    type: SettingType


@dataclass
class OrgSetting:
    organization_id: str
    name: str
    value: str


SETTING_SUBJECT_DEFAULT_DISABLED = 1
SETTING_SUBJECT_DEFAULT_OPTIONAL = 2
SETTING_SUBJECT_DEFAULT_REQUIRED = 3


SETTING_INSTALL_ID = SettingName(name="install_id", type=SettingType.string)
SETTING_DATABASE_VERSION = SettingName(name="db_version", type=SettingType.int)
SETTING_ALLOW_ANY_USER = SettingName(name="allow_any_user", type=SettingType.bool)
SETTING_CONFLUENCE_SERVER_SHARED_SECRET = SettingName(name="confluence_server_shared_secret", type=SettingType.string)
SETTING_CONFLUENCE_ANONYMOUS = SettingName(name="confluence_anonymous", type=SettingType.bool)
SETTING_MAX_BOOKINGS_PER_USER = SettingName(name="max_bookings_per_user", type=SettingType.int)
SETTING_MAX_CONCURRENT_BOOKINGS_PER_USER = SettingName(name="max_concurrent_bookings_per_user", type=SettingType.int)
SETTING_MAX_DAYS_IN_ADVANCE = SettingName(name="max_days_in_advance", type=SettingType.int)
SETTING_BOOKING_RETENTION_ENABLED = SettingName(name="booking_retention_enabled", type=SettingType.bool)
SETTING_BOOKING_RETENTION_DAYS = SettingName(name="booking_retention_days", type=SettingType.int)
SETTING_ENABLE_MAX_HOUR_BEFORE_DELETE = SettingName(name="enable_max_hours_before_delete", type=SettingType.bool)
SETTING_MAX_HOURS_BEFORE_DELETE = SettingName(name="max_hours_before_delete", type=SettingType.int)
SETTING_MIN_BOOKING_DURATION_HOURS = SettingName(name="min_booking_duration_hours", type=SettingType.int)
SETTING_MAX_BOOKING_DURATION_HOURS = SettingName(name="max_booking_duration_hours", type=SettingType.int)
SETTING_MAX_HOURS_PARTIALLY_BOOKED = SettingName(name="max_hours_partially_booked", type=SettingType.int)
SETTING_MAX_HOURS_PARTIALLY_BOOKED_ENABLED = SettingName(name="max_hours_partially_booked_enabled", type=SettingType.bool)
SETTING_DAILY_BASIS_BOOKING = SettingName(name="daily_basis_booking", type=SettingType.bool)
SETTING_NO_ADMIN_RESTRICTIONS = SettingName(name="no_admin_restrictions", type=SettingType.bool)
SETTING_CUSTOM_LOGO_URL = SettingName(name="custom_logo_url", type=SettingType.string)
SETTING_SHOW_NAMES = SettingName(name="show_names", type=SettingType.bool)
SETTING_ALLOW_BOOKINGS_NON_EXISTING_USERS = SettingName(name="allow_booking_nonexist_users", type=SettingType.bool)
SETTING_DISABLE_BUDDIES = SettingName(name="disable_buddies", type=SettingType.bool)
SETTING_DEFAULT_TIMEZONE = SettingName(name="default_timezone", type=SettingType.string)
SETTING_ALLOW_RECURRING_BOOKINGS = SettingName(name="allow_recurring_bookings", type=SettingType.bool)
SETTING_SUBJECT_DEFAULT = SettingName(name="subject_default", type=SettingType.int)

SETTING_FEATURE_NO_USER_LIMIT = SettingName(name="feature_no_user_limit", type=SettingType.bool)
SETTING_FEATURE_CUSTOM_DOMAINS = SettingName(name="feature_custom_domains", type=SettingType.bool)
SETTING_FEATURE_GROUPS = SettingName(name="feature_groups", type=SettingType.bool)
SETTING_FEATURE_AUTH_PROVIDERS = SettingName(name="feature_auth_providers", type=SettingType.bool)
SETTING_FEATURE_RECURRING_BOOKINGS = SettingName(name="feature_recurring_bookings", type=SettingType.bool)


class SettingsRepository:
    """
    Porting 1:1 del repository Go.
    - Tabella: settings(organization_id uuid, name varchar, value varchar, PK(org_id, name))
    - Cache TTL 5 minuti key = f"{org_id}_{name}"
    """

    CACHE_TTL_SECONDS = 60 * 5

    def ensure_table(self, db: Session) -> None:
        
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    organization_id uuid NOT NULL,
                    name VARCHAR NOT NULL,
                    value VARCHAR NOT NULL DEFAULT '',
                    PRIMARY KEY (organization_id, name)
                )
                """
            )
        )
        db.commit()

    
    def run_schema_upgrade(self, db: Session, cur_version: int, target_version: int, default_user_limit: int) -> None:
        """
        Go:
          SELECT organization_id FROM settings
          WHERE name='subscription_max_users' AND NULLIF(value,'')::int > DefaultUserLimit
        Poi:
          Set feature_no_user_limit=1
          Set feature_custom_domains=1
          Delete subscription_max_users
        """
        rows = db.execute(
            text(
                """
                SELECT organization_id
                FROM settings
                WHERE name = 'subscription_max_users'
                  AND NULLIF(value, '')::int > :default_user_limit
                """
            ),
            {"default_user_limit": default_user_limit},
        ).fetchall()

        for (org_id,) in rows:
            org_id_str = str(org_id)
            self.set(db, org_id_str, SETTING_FEATURE_NO_USER_LIMIT.name, "1")
            self.set(db, org_id_str, SETTING_FEATURE_CUSTOM_DOMAINS.name, "1")
            self.delete(db, org_id_str, "subscription_max_users")

    
    def set(self, db: Session, organization_id: str, name: str, value: str) -> None:
        db.execute(
            text(
                """
                INSERT INTO settings (organization_id, name, value)
                VALUES (:org_id, :name, :value)
                ON CONFLICT (organization_id, name) DO UPDATE SET value = :value
                """
            ),
            {"org_id": organization_id, "name": name, "value": value},
        )
        db.commit()
        get_cache().set(f"{organization_id}_{name}", value.encode("utf-8"), self.CACHE_TTL_SECONDS)

    def delete(self, db: Session, organization_id: str, name: str) -> None:
        db.execute(
            text("DELETE FROM settings WHERE organization_id = :org_id AND name = :name"),
            {"org_id": organization_id, "name": name},
        )
        db.commit()
        get_cache().delete(f"{organization_id}_{name}")

    def get(self, db: Session, organization_id: str, name: str) -> str:
        
        cache_key = f"{organization_id}_{name}"
        try:
            return get_cache().get(cache_key).decode("utf-8")
        except KeyError:
            pass

        row = db.execute(
            text("SELECT value FROM settings WHERE organization_id = :org_id AND name = :name"),
            {"org_id": organization_id, "name": name},
        ).fetchone()

        if row is None:
            
            raise KeyError(f"setting not found: org={organization_id} name={name}")

        res = str(row[0])
        get_cache().set(cache_key, res.encode("utf-8"), self.CACHE_TTL_SECONDS)
        return res

    def get_organization_ids_by_value(self, db: Session, name: str, value: str) -> List[str]:
        rows = db.execute(
            text("SELECT organization_id FROM settings WHERE name = :name AND value = :value"),
            {"name": name, "value": value},
        ).fetchall()
        return [str(r[0]) for r in rows]

    
    def get_org_ids_by_value(self, db: Session, name: str, value: str) -> List[str]:
        rows = db.execute(
            text(
                """
                SELECT organization_id
                FROM settings
                WHERE name = :name AND value = :value
                ORDER BY organization_id
                """
            ),
            {"name": name, "value": value},
        ).fetchall()
        return [str(r[0]) for r in rows]

    
    def set_global(self, db: Session, name: str, value: str) -> None:
        self.set(db, self.get_null_uuid(), name, value)

    def get_global_string(self, db: Session, name: str) -> str:
        return self.get(db, self.get_null_uuid(), name)

    def get_global_int(self, db: Session, name: str) -> int:
        return int(self.get(db, self.get_null_uuid(), name))

    def get_global_bool(self, db: Session, name: str) -> bool:
        return self.get(db, self.get_null_uuid(), name) == "1"

    
    def get_int(self, db: Session, organization_id: str, name: str) -> int:
        return int(self.get(db, organization_id, name))

    def get_bool(self, db: Session, organization_id: str, name: str) -> bool:
        return self.get(db, organization_id, name) == "1"

    
    def get_all(self, db: Session, organization_id: str) -> List[OrgSetting]:
        rows = db.execute(
            text(
                """
                SELECT organization_id, name, value
                FROM settings
                WHERE organization_id = :org_id
                ORDER BY name
                """
            ),
            {"org_id": organization_id},
        ).fetchall()

        result: List[OrgSetting] = []
        for org_id, name, value in rows:
            s = OrgSetting(organization_id=str(org_id), name=str(name), value=str(value))
            result.append(s)
            get_cache().set(f"{organization_id}_{s.name}", s.value.encode("utf-8"), self.CACHE_TTL_SECONDS)
        return result

    
    def init_default_settings_for_org(self, db: Session, organization_id: str) -> None:
        """
        Porting 1:1 della INSERT multi-values del Go con ON CONFLICT DO NOTHING.
        """
        db.execute(
            text(
                f"""
                INSERT INTO settings (organization_id, name, value)
                VALUES
                    (:org_id, '{SETTING_FEATURE_NO_USER_LIMIT.name}', '0'),
                    (:org_id, '{SETTING_FEATURE_CUSTOM_DOMAINS.name}', '0'),
                    (:org_id, '{SETTING_FEATURE_GROUPS.name}', '0'),
                    (:org_id, '{SETTING_ALLOW_ANY_USER.name}', '1'),
                    (:org_id, '{SETTING_DAILY_BASIS_BOOKING.name}', '0'),
                    (:org_id, '{SETTING_NO_ADMIN_RESTRICTIONS.name}', '0'),
                    (:org_id, '{SETTING_CUSTOM_LOGO_URL.name}', ''),
                    (:org_id, '{SETTING_SHOW_NAMES.name}', '0'),
                    (:org_id, '{SETTING_ALLOW_BOOKINGS_NON_EXISTING_USERS.name}', '0'),
                    (:org_id, '{SETTING_DISABLE_BUDDIES.name}', '0'),
                    (:org_id, '{SETTING_CONFLUENCE_SERVER_SHARED_SECRET.name}', ''),
                    (:org_id, '{SETTING_CONFLUENCE_ANONYMOUS.name}', '0'),
                    (:org_id, '{SETTING_MAX_BOOKINGS_PER_USER.name}', '10'),
                    (:org_id, '{SETTING_MAX_CONCURRENT_BOOKINGS_PER_USER.name}', '0'),
                    (:org_id, '{SETTING_ENABLE_MAX_HOUR_BEFORE_DELETE.name}', '0'),
                    (:org_id, '{SETTING_MAX_HOURS_BEFORE_DELETE.name}', '0'),
                    (:org_id, '{SETTING_MAX_HOURS_PARTIALLY_BOOKED_ENABLED.name}', '0'),
                    (:org_id, '{SETTING_MAX_HOURS_PARTIALLY_BOOKED.name}', '8'),
                    (:org_id, '{SETTING_MIN_BOOKING_DURATION_HOURS.name}', '0'),
                    (:org_id, '{SETTING_MAX_DAYS_IN_ADVANCE.name}', '14'),
                    (:org_id, '{SETTING_MAX_BOOKING_DURATION_HOURS.name}', '12'),
                    (:org_id, '{SETTING_DEFAULT_TIMEZONE.name}', 'Europe/Berlin'),
                    (:org_id, '{SETTING_ALLOW_RECURRING_BOOKINGS.name}', '1'),
                    (:org_id, '{SETTING_BOOKING_RETENTION_ENABLED.name}', '0'),
                    (:org_id, '{SETTING_BOOKING_RETENTION_DAYS.name}', '365'),
                    (:org_id, '{SETTING_SUBJECT_DEFAULT.name}', '{SETTING_SUBJECT_DEFAULT_OPTIONAL}')
                ON CONFLICT (organization_id, name) DO NOTHING
                """
            ),
            {"org_id": organization_id},
        )
        db.commit()

    def init_default_settings(self, db: Session, org_ids: Sequence[str]) -> None:
        for org_id in org_ids:
            self.init_default_settings_for_org(db, org_id)

    def delete_all(self, db: Session, organization_id: str) -> None:
        db.execute(
            text("DELETE FROM settings WHERE organization_id = :org_id"),
            {"org_id": organization_id},
        )
        db.commit()

    @staticmethod
    def get_null_uuid() -> str:
        return "00000000-0000-0000-0000-000000000000"


_settings_repo_singleton: Optional[SettingsRepository] = None


def get_settings_repository() -> SettingsRepository:
    global _settings_repo_singleton
    if _settings_repo_singleton is None:
        _settings_repo_singleton = SettingsRepository()
    return _settings_repo_singleton