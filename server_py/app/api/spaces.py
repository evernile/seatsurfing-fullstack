import json
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Space, Location, User
from app.repositories.space_repository import SpaceRepository
from app.repositories.group_repository import GroupRepository
from app.schemas.space import (
    CreateSpaceRequest,
    GetSpaceResponse,
    SpaceBulkUpdateRequest,
    BulkUpdateResponse,
    BulkUpdateItemResponse,
    GetSpaceAvailabilityResponse,
    GetSpaceAvailabilityBookingsResponse,
)

router = APIRouter(prefix="/locations/{location_id}/spaces", tags=["spaces"])
spaces_repo = SpaceRepository()
group_repo = GroupRepository()


def can_access_org(user: User, org_id: str) -> bool:
    return bool(user.organization_id) and user.organization_id == org_id


def can_space_admin_org(user: User, org_id: str) -> bool:
    return can_access_org(user, org_id) and user.role == "admin"


def _get_location_or_400(db: Session, location_id: str) -> Location:
    try:
        lid = uuid.UUID(location_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid location id")

    loc = db.query(Location).filter(Location.id == lid).first()
    if not loc:
        raise HTTPException(status_code=400, detail="Location not found")
    return loc


def _space_to_get_response(
    space: Space,
    location_id: str,
    available: bool,
    approver_ids: list[str],
    allowed_booker_ids: list[str],
) -> GetSpaceResponse:
    return GetSpaceResponse(
        id=str(space.public_id),
        available=available,
        locationId=location_id,
        name=space.name,
        x=int(space.x or 0),
        y=int(space.y or 0),
        width=int(space.width or 0),
        height=int(space.height or 0),
        rotation=int(space.rotation or 0),
        requireSubject=bool(space.require_subject),
        attributes=[],  # TODO: space_attribute_values
        approverGroupIds=approver_ids,
        allowedBookerGroupIds=allowed_booker_ids,
    )


@router.get("/", response_model=list[GetSpaceResponse])
def get_all_spaces(
    location_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_access_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    spaces = spaces_repo.get_all(db, location_id)
    space_ids = [str(s.public_id) for s in spaces]

    approvers = spaces_repo.get_all_approvers_for_space_list(db, space_ids)
    allowed = spaces_repo.get_all_allowed_bookers_for_space_list(db, space_ids)

    approver_by_space: dict[str, list[str]] = {}
    for a in approvers:
        approver_by_space.setdefault(a.space_id, []).append(a.group_id)

    allowed_by_space: dict[str, list[str]] = {}
    for a in allowed:
        allowed_by_space.setdefault(a.space_id, []).append(a.group_id)

    return [
        _space_to_get_response(
            s,
            location_id,
            False,
            sorted(approver_by_space.get(str(s.public_id), [])),
            sorted(allowed_by_space.get(str(s.public_id), [])),
        )
        for s in spaces
    ]


@router.get("/availability", response_model=list[GetSpaceAvailabilityResponse])
def get_availability(
    location_id: str,
    enter: datetime | None = Query(default=None),
    leave: datetime | None = Query(default=None),
    attributes: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_access_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # default enter/leave
    if enter is None or leave is None:
        now = datetime.now(timezone.utc)
        enter = now - timedelta(minutes=1)
        leave = now + timedelta(minutes=1)

    # attributes: per ora validiamo solo JSON
    if attributes:
        try:
            json.loads(attributes)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid attributes JSON")

    avail_list = spaces_repo.get_all_in_time(db, location_id, enter, leave)

    space_ids = [str(x.space.public_id) for x in avail_list]
    approvers = spaces_repo.get_all_approvers_for_space_list(db, space_ids)
    allowed = spaces_repo.get_all_allowed_bookers_for_space_list(db, space_ids)

    # gruppi dell'utente (mi aspetto list[str] -> set[str])
    user_group_ids = set(group_repo.get_user_group_ids(db, str(current_user.public_id)) or [])

    # indicizzazione: space_id -> set[group_id]
    approver_groups_by_space: dict[str, set[str]] = {}
    for a in approvers:
        approver_groups_by_space.setdefault(a.space_id, set()).add(a.group_id)

    allowed_groups_by_space: dict[str, set[str]] = {}
    for a in allowed:
        allowed_groups_by_space.setdefault(a.space_id, set()).add(a.group_id)

    def is_allowed(space_public_id: str) -> bool:
        allowed_groups = allowed_groups_by_space.get(space_public_id, set())
        if not allowed_groups:
            return True  # nessuna restriction
        return len(allowed_groups.intersection(user_group_ids)) > 0

    def approval_required(space_public_id: str) -> bool:
        return len(approver_groups_by_space.get(space_public_id, set())) > 0

    def user_is_approver(space_public_id: str) -> bool:
        approver_groups = approver_groups_by_space.get(space_public_id, set())
        if not approver_groups:
            return False
        return len(approver_groups.intersection(user_group_ids)) > 0

    show_names = current_user.role == "admin"

    res: list[GetSpaceAvailabilityResponse] = []
    for item in avail_list:
        sp = item.space
        sid = str(sp.public_id)

        out = GetSpaceAvailabilityResponse(
            id=sid,
            available=item.available,
            locationId=location_id,
            name=sp.name,
            x=int(sp.x or 0),
            y=int(sp.y or 0),
            width=int(sp.width or 0),
            height=int(sp.height or 0),
            rotation=int(sp.rotation or 0),
            requireSubject=bool(sp.require_subject),
            attributes=[],
            approverGroupIds=sorted(list(approver_groups_by_space.get(sid, set()))),
            allowedBookerGroupIds=sorted(list(allowed_groups_by_space.get(sid, set()))),
            bookings=[],
            allowed=is_allowed(sid),
            approvalRequired=approval_required(sid),
            # Se nel tuo schema esiste, scommenta:
            # canApprove=user_is_approver(sid),
        )

        for b in item.bookings:
            out_user_id = ""
            out_user_email = ""
            if show_names or current_user.email == b.user_email:
                out_user_id = b.user_id
                out_user_email = b.user_email

            out.bookings.append(
                GetSpaceAvailabilityBookingsResponse(
                    id=b.booking_id,
                    recurringId=b.recurring_id,
                    userId=out_user_id,
                    userEmail=out_user_email,
                    enter=b.enter,
                    leave=b.leave,
                    subject=b.subject,
                )
            )

        res.append(out)

    return res


@router.get("/{space_id}", response_model=GetSpaceResponse)
def get_one_space(
    location_id: str,
    space_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_access_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    sp = spaces_repo.get_one(db, space_id)
    if not sp or str(sp.location_id) != str(loc.id):
        raise HTTPException(status_code=404, detail="Space not found")

    approvers = spaces_repo.get_approver_group_ids(db, space_id)
    allowed = spaces_repo.get_allowed_bookers_group_ids(db, space_id)

    return _space_to_get_response(sp, location_id, False, approvers, allowed)


@router.post("/", status_code=201)
def create_space(
    location_id: str,
    payload: CreateSpaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_space_admin_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    sp = Space(
        organization_id=loc.organization_id,
        location_id=loc.id,
        name=payload.name,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
        rotation=payload.rotation,
        require_subject=payload.require_subject,
    )
    sp = spaces_repo.create(db, sp)

    if payload.approver_group_ids:
        spaces_repo.add_approvers(db, str(sp.public_id), payload.approver_group_ids)
    if payload.allowed_booker_group_ids:
        spaces_repo.add_allowed_bookers(db, str(sp.public_id), payload.allowed_booker_group_ids)

    return {"id": str(sp.public_id)}


@router.put("/{space_id}", status_code=200)
def update_space(
    location_id: str,
    space_id: str,
    payload: CreateSpaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_space_admin_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    sp = spaces_repo.get_one(db, space_id)
    if not sp or str(sp.location_id) != str(loc.id):
        raise HTTPException(status_code=404, detail="Space not found")

    sp.name = payload.name
    sp.x = payload.x
    sp.y = payload.y
    sp.width = payload.width
    sp.height = payload.height
    sp.rotation = payload.rotation
    sp.require_subject = payload.require_subject

    spaces_repo.update(db, sp)

    # NB: come avevi già scritto: approvers/allowed li gestisci con bulk (diff)
    return {"status": "updated"}


@router.delete("/{space_id}", status_code=200)
def delete_space(
    location_id: str,
    space_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_space_admin_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    sp = spaces_repo.get_one(db, space_id)
    if not sp or str(sp.location_id) != str(loc.id):
        raise HTTPException(status_code=404, detail="Space not found")

    spaces_repo.delete(db, sp)
    return {"status": "updated"}


@router.post("/bulk", response_model=BulkUpdateResponse)
def bulk_update(
    location_id: str,
    payload: SpaceBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loc = _get_location_or_400(db, location_id)
    if not can_space_admin_org(current_user, loc.organization_id):
        raise HTTPException(status_code=403, detail="Forbidden")

    creates: list[BulkUpdateItemResponse] = []
    updates: list[BulkUpdateItemResponse] = []
    deletes: list[BulkUpdateItemResponse] = []

    # deletes
    for did in payload.delete_ids or []:
        sp = spaces_repo.get_one(db, did)
        if not sp or str(sp.location_id) != str(loc.id):
            deletes.append(BulkUpdateItemResponse(id=did, success=False))
            continue
        try:
            spaces_repo.delete(db, sp)
            deletes.append(BulkUpdateItemResponse(id=did, success=True))
        except Exception:
            deletes.append(BulkUpdateItemResponse(id=did, success=False))

    # creates
    for c in payload.creates or []:
        try:
            sp = Space(
                organization_id=loc.organization_id,
                location_id=loc.id,
                name=c.name,
                x=c.x,
                y=c.y,
                width=c.width,
                height=c.height,
                rotation=c.rotation,
                require_subject=c.require_subject,
            )
            sp = spaces_repo.create(db, sp)

            if c.approver_group_ids:
                spaces_repo.add_approvers(db, str(sp.public_id), c.approver_group_ids)
            if c.allowed_booker_group_ids:
                spaces_repo.add_allowed_bookers(db, str(sp.public_id), c.allowed_booker_group_ids)

            creates.append(BulkUpdateItemResponse(id=str(sp.public_id), success=True))
        except Exception:
            creates.append(BulkUpdateItemResponse(id="", success=False))

    # updates
    for u in payload.updates or []:
        try:
            sp = spaces_repo.get_one(db, u.id)
            if not sp or str(sp.location_id) != str(loc.id):
                updates.append(BulkUpdateItemResponse(id=u.id, success=False))
                continue

            sp.name = u.name
            sp.x = u.x
            sp.y = u.y
            sp.width = u.width
            sp.height = u.height
            sp.rotation = u.rotation
            sp.require_subject = u.require_subject
            sp.location_id = loc.id
            spaces_repo.update(db, sp)

            # diff approvers
            existing_app = set(spaces_repo.get_approver_group_ids(db, u.id))
            new_app = set(u.approver_group_ids or [])
            spaces_repo.add_approvers(db, u.id, list(new_app - existing_app))
            spaces_repo.remove_approvers(db, u.id, list(existing_app - new_app))

            # diff allowed bookers
            existing_all = set(spaces_repo.get_allowed_bookers_group_ids(db, u.id))
            new_all = set(u.allowed_booker_group_ids or [])
            spaces_repo.add_allowed_bookers(db, u.id, list(new_all - existing_all))
            spaces_repo.remove_allowed_bookers(db, u.id, list(existing_all - new_all))

            updates.append(BulkUpdateItemResponse(id=str(sp.public_id), success=True))
        except Exception:
            updates.append(BulkUpdateItemResponse(id=u.id if getattr(u, "id", None) else "", success=False))

    return BulkUpdateResponse(creates=creates, updates=updates, deletes=deletes)