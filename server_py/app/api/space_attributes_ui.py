from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User

router = APIRouter(prefix="/space-attribute", tags=["ui-compat"])


@router.get("/")
def list_space_attributes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    rows = db.execute(
        text("""
            SELECT
                id,
                label,
                type,
                location_applicable,
                space_applicable
            FROM space_attributes
            WHERE organization_id = :org_id
            ORDER BY label
        """),
        {"org_id": str(current_user.organization_id)},
    ).mappings().all()

    result = []
    for r in rows:
        result.append({
            "id": str(r["id"]),
            "label": r["label"],
            "name": r["label"],
            "type": r["type"],
            "locationApplicable": bool(r["location_applicable"]),
            "spaceApplicable": bool(r["space_applicable"]),
        })

    return result


@router.post("/")
def create_space_attribute(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    label = payload.get("label")
    attr_type = payload.get("type")
    location_applicable = payload.get("locationApplicable", False)
    space_applicable = payload.get("spaceApplicable", False)

    if not label:
        raise HTTPException(status_code=400, detail="Missing label")

    if attr_type is None:
        raise HTTPException(status_code=400, detail="Missing type")

    db.execute(
        text("""
            INSERT INTO space_attributes (
                id,
                organization_id,
                label,
                type,
                location_applicable,
                space_applicable
            )
            VALUES (
                gen_random_uuid(),
                :org_id,
                :label,
                :type,
                :location_applicable,
                :space_applicable
            )
        """),
        {
            "org_id": str(current_user.organization_id),
            "label": label,
            "type": int(attr_type),
            "location_applicable": bool(location_applicable),
            "space_applicable": bool(space_applicable),
        },
    )

    db.commit()
    return {"status": "created"}


@router.delete("/{attribute_id}")
def delete_space_attribute(
    attribute_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    db.execute(
        text("""
            DELETE FROM space_attributes
            WHERE id = :id
              AND organization_id = :org_id
        """),
        {
            "id": attribute_id,
            "org_id": str(current_user.organization_id),
        },
    )

    db.commit()
    return {"status": "deleted"}