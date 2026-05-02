import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Text,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)

    contact_firstname = Column(String, nullable=True)
    contact_lastname = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    language = Column(String, nullable=True)
    signup_date = Column(DateTime, nullable=True)

    country = Column(String, nullable=False, default="")
    address_line1 = Column(String, nullable=False, default="")
    address_line2 = Column(String, nullable=False, default="")
    postal_code = Column(String, nullable=False, default="")
    city = Column(String, nullable=False, default="")
    vat_id = Column(String, nullable=False, default="")
    company = Column(String, nullable=False, default="")

    domains = relationship("OrganizationDomain", back_populates="organization")
    users = relationship("User", back_populates="organization")
    locations = relationship("Location", back_populates="organization")


class OrganizationDomain(Base):
    """
    Go: CREATE TABLE organizations_domains (
        domain VARCHAR NOT NULL PRIMARY KEY,
        organization_id uuid NOT NULL,
        active boolean NOT NULL DEFAULT FALSE,
        verify_token uuid,
        primary_domain boolean NOT NULL DEFAULT FALSE,
        accessible boolean NOT NULL DEFAULT FALSE,
        access_check TIMESTAMP NULL DEFAULT NULL
    )
    """
    __tablename__ = "organizations_domains"

    
    domain = Column(String, primary_key=True)

    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    active = Column(Boolean, nullable=False, default=False)
    verify_token = Column(UUID(as_uuid=True), nullable=True)

    primary_domain = Column(Boolean, nullable=False, default=False)
    accessible = Column(Boolean, nullable=False, default=False)
    access_check = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="domains")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)

    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)

    
    hashed_password = Column("password", String, nullable=True)

    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    role = Column(Integer, nullable=False, default=0)

    organization = relationship("Organization", back_populates="users")
    bookings = relationship("Booking", back_populates="user")

    @property
    def full_name(self) -> str:
        fn = (self.firstname or "").strip()
        ln = (self.lastname or "").strip()
        return (fn + " " + ln).strip()


class AuthAttempt(Base):
    __tablename__ = "auth_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # Go: uuid NULL (no FK in Go)
    email = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    successful = Column(Boolean, nullable=True)

    _table_args_ = (
        Index("idx_auth_attempts_user_id", "user_id"),
        Index("idx_auth_attempts_email", "email"),
    )


class AuthProvider(Base):
    __tablename__ = "auth_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False)  # Go: uuid NOT NULL
    name = Column(String, nullable=False)

    provider_type = Column(Integer, nullable=False)  # Go: INT NOT NULL
    auth_url = Column(String, nullable=False)
    token_url = Column(String, nullable=False)
    auth_style = Column(Integer, nullable=False)
    scopes = Column(String, nullable=False)
    userinfo_url = Column(String, nullable=False)
    userinfo_email_field = Column(String, nullable=False)

    userinfo_firstname_field = Column(String, nullable=False, default="")
    userinfo_lastname_field = Column(String, nullable=False, default="")

    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)

    logout_url = Column(String, nullable=False, default="")
    profile_page_url = Column(String, nullable=False, default="")
    read_only = Column(Boolean, nullable=False, default=False)

    _table_args_ = (
        Index("idx_auth_providers_organization_id", "organization_id"),
    )


class AuthState(Base):
    __tablename__ = "auth_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth_provider_id = Column(UUID(as_uuid=True), nullable=False)  # Go: uuid NOT NULL
    expiry = Column(DateTime, nullable=False)
    auth_state_type = Column(Integer, nullable=False)  # Go enum stored as INT
    payload = Column(String, nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    created = Column(DateTime, nullable=False)
    expiry = Column(DateTime, nullable=False)

    user = relationship("User")


class MailLog(Base):
    __tablename__ = "mail_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    timestamp = Column(DateTime, nullable=False, index=True)
    subject = Column(String, nullable=False)
    recipient = Column(String, nullable=False, index=True)

    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)

    organization = relationship("Organization")


class DebugTimeIssueItem(Base):
    __tablename__ = "debug_time_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created = Column(DateTime, nullable=False)


class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # DB Go: organization_id uuid
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    name = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_groups_org_name"),
    )


class UserGroup(Base):
    __tablename__ = "users_groups"

    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)

    # Go: users_groups.user_id uuid -> riferisce users.id
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    name = Column(String, nullable=False)

    description = Column(String, nullable=True)
    
    enabled = Column(Boolean, nullable=False, default=True)

    organization = relationship("Organization", back_populates="locations")
    spaces = relationship("Space", back_populates="location_rel")


class Space(Base):
    __tablename__ = "spaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False, index=True)

    name = Column(String, nullable=False)

    x = Column(Integer, nullable=True)
    y = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    rotation = Column(Integer, nullable=True)

    require_subject = Column(Boolean, nullable=False, default=True)

    location_rel = relationship("Location", back_populates="spaces")
    bookings = relationship("Booking", back_populates="space")


class SpaceApprover(Base):
    __tablename__ = "spaces_approvers"

    space_id = Column(UUID(as_uuid=True), ForeignKey("spaces.id"), primary_key=True)
    group_id = Column(UUID(as_uuid=True), primary_key=True)


class SpaceAllowedBooker(Base):
    __tablename__ = "spaces_allowed_bookers"

    space_id = Column(UUID(as_uuid=True), ForeignKey("spaces.id"), primary_key=True)
    group_id = Column(UUID(as_uuid=True), primary_key=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    space_id = Column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False, index=True)

    enter_time = Column(DateTime, nullable=False, index=True)
    leave_time = Column(DateTime, nullable=False, index=True)

    caldav_id = Column(String, nullable=False, default="")
    approved = Column(Boolean, nullable=False, default=True)
    subject = Column(String, nullable=False, default="")

    recurring_id = Column(UUID(as_uuid=True), nullable=True)

    created_at_utc = Column(DateTime, nullable=True, default=datetime.utcnow)

    user = relationship("User", back_populates="bookings")
    space = relationship("Space", back_populates="bookings")

class RecurringBooking(Base):
    __tablename__ = "recurring_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    space_id = Column(UUID(as_uuid=True), ForeignKey("spaces.id"), nullable=False)

    enter_time = Column(DateTime, nullable=False)
    leave_time = Column(DateTime, nullable=False)

    subject = Column(String, nullable=False, default="")

    cadence = Column(Integer, nullable=False)

    details = Column(String)

    end_date = Column(DateTime, nullable=False)

    user = relationship("User")
    space = relationship("Space")