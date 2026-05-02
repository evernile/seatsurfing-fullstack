from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.schemas.booking import BookingCreate, BookingOut
from app.repositories.booking_repository import BookingRepository
from app.repositories.space_repository import SpaceRepository
from app.repositories.group_repository import GroupRepository

from app.services.mail_service import send_calendar_invite, build_booking_email_html, MAIL_FROM, MAIL_FROM_NAME
from app.services.calendar_invite_service import build_booking_invite_ics

router = APIRouter(prefix="/bookings", tags=["bookings"])

repo = BookingRepository()
spaces_repo = SpaceRepository()
group_repo = GroupRepository()


ADMIN_ROLES = {"org_admin", "super_admin", "admin"}


def _is_admin(user: User) -> bool:
    return user.role in ADMIN_ROLES


def _send_booking_confirmation_email(booking, current_user: User, space, payload: BookingCreate) -> None:
    """
    Invia email HTML + allegato .ics dopo la creazione della prenotazione.
    La chiamata è protetta da try/except per non bloccare la prenotazione
    se l'invio email fallisce.
    """
    try:
        to_email = current_user.email

        if not to_email or to_email.endswith(".local"):
            return

        location_name = "Sede selezionata"
        if getattr(space, "location", None):
            location_name = getattr(space.location, "name", location_name)

        space_name = getattr(space, "name", "Spazio prenotato")
        subject_text = getattr(payload, "subject", None) or "Prenotazione via chat"

        start_text = payload.start_at.strftime("%d/%m/%Y %H:%M")
        end_text = payload.end_at.strftime("%d/%m/%Y %H:%M")

        email_subject = f"Prenotazione confermata - {space_name}"

        body_text = (
            "La tua prenotazione è stata registrata.\n\n"
            f"Sede: {location_name}\n"
            f"Spazio: {space_name}\n"
            f"Inizio: {start_text}\n"
            f"Fine: {end_text}\n"
            f"Oggetto: {subject_text}\n\n"
            "Apri l'invito allegato per aggiungerlo al calendario."
        )

        body_html = build_booking_email_html(
            location_name=location_name,
            space_name=space_name,
            start_text=start_text,
            end_text=end_text,
            subject_text=subject_text,
        )

        ics_content = build_booking_invite_ics(
            booking_id=str(getattr(booking, "id", "")),
            start_dt=payload.start_at,
            end_dt=payload.end_at,
            attendee_email=to_email,
            summary=f"SeatSurfing - {space_name}",
            description=f"Prenotazione SeatSurfing: {space_name}",
            location=location_name,
            organizer_email=MAIL_FROM,
            organizer_name=MAIL_FROM_NAME,
        )

        send_calendar_invite(
            to_email=to_email,
            subject=email_subject,
            body_text=body_text,
            body_html=body_html,
            ics_content=ics_content,
            filename=f"booking-{getattr(booking, 'id', 'seatsurfing')}.ics",
        )

    except Exception as e:
        print(f"[MAIL] Errore invio email prenotazione: {e}")


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    if payload.end_at <= payload.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")

    space = spaces_repo.get_by_id_in_org(db, current_user.organization_id, payload.space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    if hasattr(space, "is_active") and not space.is_active:
        raise HTTPException(status_code=400, detail="Space not active")

    space_public_id = str(space.public_id)

   
    user_group_ids = set(group_repo.get_user_group_ids(db, str(current_user.public_id)) or [])

    
    allowed_group_ids = set(spaces_repo.get_allowed_bookers_group_ids(db, space_public_id))
    if allowed_group_ids and not _is_admin(current_user):
        if not allowed_group_ids.intersection(user_group_ids):
            raise HTTPException(status_code=403, detail="User not allowed to book this space")

    
    if repo.overlaps(db, current_user.organization_id, payload.space_id, payload.start_at, payload.end_at):
        raise HTTPException(status_code=409, detail="Time slot not available")

    
    approver_group_ids = set(spaces_repo.get_approver_group_ids(db, space_public_id))

    needs_approval = bool(approver_group_ids)
    is_approver = bool(approver_group_ids.intersection(user_group_ids))

    if needs_approval and not (_is_admin(current_user) or is_approver):
        booking_status = "pending"
    else:
        booking_status = "approved"

    booking = repo.create(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,     
        space_id=payload.space_id,  
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=booking_status,
    )

    _send_booking_confirmation_email(
        booking=booking,
        current_user=current_user,
        space=space,
        payload=payload,
    )

    return booking


@router.get("", response_model=list[BookingOut])
def list_bookings(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    
    if current_user.role in ADMIN_ROLES:
        if status:
            return repo.list_by_status_in_org(db, current_user.organization_id, status)
        return repo.list_by_org(db, current_user.organization_id)
    
    if status == "pending":
        return repo.list_pending_for_approver(
            db,
            current_user.organization_id,
            str(current_user.public_id),
        )

    if _is_admin(current_user):
        return repo.list_by_org(db, current_user.organization_id)

    return repo.list_by_user_in_org(db, current_user.organization_id, current_user.id)


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    if _is_admin(current_user):
        booking = repo.get_by_id_in_org(db, current_user.organization_id, booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        if booking.status == "approved" and current_user.role not in ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Approved booking cannot be deleted")
        
        if current_user.role in ADMIN_ROLES:
            ok = repo.soft_delete_in_org(db, current_user.organization_id, booking_id)
        else:
            ok = repo.soft_delete_for_user_in_org(
                db,
                current_user.organization_id,
                booking_id,
                current_user.id
            )
        if not ok:
            raise HTTPException(status_code=404, detail="Booking not found")
        return None

    booking = repo.get_by_id_for_user_in_org(db, current_user.organization_id, booking_id, current_user.id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.post("/{booking_id}/approve", status_code=200)
def approve_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    booking = repo.get_by_id_in_org(db, current_user.organization_id, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not pending")

    
    space = booking.space
    approver_groups = set(spaces_repo.get_approver_group_ids(db, str(space.public_id)))

    if not _is_admin(current_user):
        user_group_ids = set(group_repo.get_user_group_ids(db, str(current_user.public_id)) or [])
        if approver_groups and not approver_groups.intersection(user_group_ids):
            raise HTTPException(status_code=403, detail="Not an approver")

    booking.status = "approved"
    booking.approved_by = current_user.public_id
    booking.approved_at = datetime.utcnow()

    db.commit()
    return {"status": "approved"}


@router.post("/{booking_id}/reject", status_code=200)
def reject_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    booking = repo.get_by_id_in_org(db, current_user.organization_id, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not pending")

    space = booking.space
    approver_groups = set(spaces_repo.get_approver_group_ids(db, str(space.public_id)))

    if not _is_admin(current_user):
        user_group_ids = set(group_repo.get_user_group_ids(db, str(current_user.public_id)) or [])
        if approver_groups and not approver_groups.intersection(user_group_ids):
            raise HTTPException(status_code=403, detail="Not an approver")

    
    booking.status = "rejected"
    booking.approved_by = current_user.public_id
    booking.approved_at = datetime.utcnow()
    booking.is_active = False

    db.commit()
    return {"status": "rejected"}


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    if _is_admin(current_user):
        ok = repo.soft_delete_in_org(db, current_user.organization_id, booking_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Booking not found")
        return None

    ok = repo.soft_delete_for_user_in_org(db, current_user.organization_id, booking_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Booking not found")
    return None