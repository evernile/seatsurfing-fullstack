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

router = APIRouter(prefix="/bookings", tags=["bookings"])

repo = BookingRepository()
spaces_repo = SpaceRepository()
group_repo = GroupRepository()

# NB: allinea questi ruoli al tuo sistema reale.
# In altri file usi "admin". Qui avevi "org_admin/super_admin".
ADMIN_ROLES = {"org_admin", "super_admin", "admin"}


def _is_admin(user: User) -> bool:
    return user.role in ADMIN_ROLES


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

    # Gruppi utente (uuid string)
    user_group_ids = set(group_repo.get_user_group_ids(db, str(current_user.public_id)) or [])

    # Allowed bookers: se configurato, devi appartenere almeno a un gruppo allowed (admin bypass)
    allowed_group_ids = set(spaces_repo.get_allowed_bookers_group_ids(db, space_public_id))
    if allowed_group_ids and not _is_admin(current_user):
        if not allowed_group_ids.intersection(user_group_ids):
            raise HTTPException(status_code=403, detail="User not allowed to book this space")

    # Overlap (pending + approved bloccano)
    if repo.overlaps(db, current_user.organization_id, payload.space_id, payload.start_at, payload.end_at):
        raise HTTPException(status_code=409, detail="Time slot not available")

    # Approvers -> se lo spazio ha approvers allora status=pending (salvo admin o approver)
    approver_group_ids = set(spaces_repo.get_approver_group_ids(db, space_public_id))

    needs_approval = bool(approver_group_ids)
    is_approver = bool(approver_group_ids.intersection(user_group_ids))

    if needs_approval and not (_is_admin(current_user) or is_approver):
        booking_status = "pending"
    else:
        booking_status = "approved"

    return repo.create(
        db=db,
        organization_id=current_user.organization_id,
        user_id=current_user.id,     # int
        space_id=payload.space_id,   # int
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=booking_status,
    )


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

    # autorizzazione: admin oppure approver del space
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

    # rifiuto = non deve più bloccare lo slot
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