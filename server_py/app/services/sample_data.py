import pathlib
from sqlalchemy.orm import Session

from app.models import Location, Space


def create_sample_data(db: Session, org_id: str) -> None:
    # Se esiste già la location “Sample Floor” per quell’org, non ricreare tutto
    location = (
        db.query(Location)
        .filter(Location.organization_id == org_id, Location.name == "Sample Floor")
        .first()
    )

    if not location:
        location = Location(
            organization_id=org_id,
            name="Sample Floor",
            description=(
                "Sample Map provided by Marco Garbelini under the "
                "Creative Commons Attribution 2.0 Generic (CC BY 2.0) License"
            ),
            timezone="Europe/Rome",
            enabled=True,
            map_scale=1.0,
            max_concurrent_bookings=0,
        )
        db.add(location)
        db.flush()  # così location.id è disponibile

        # Carica immagine
        base_dir = pathlib.Path(__file__).resolve().parents[2]  # server_py/
        map_path = base_dir / "res" / "floorplan.jpg"
        if not map_path.exists():
            raise FileNotFoundError(f"floorplan.jpg non trovato in: {map_path}")

        location.map_data = map_path.read_bytes()
        location.map_mimetype = "jpeg"  # come Go
        location.map_width = 2047       # come Go (se vuoi essere identica)
        location.map_height = 802

        db.commit()
        db.refresh(location)

    # Dati desk (17)
    spaces_data = [
        ("Conference 1", 990, 76, 204, 70),
        ("Desk 1", 755, 60, 120, 55),
        ("Desk 2", 843, 337, 108, 53),
        ("Desk 3", 624, 518, 104, 52),
        ("Desk 4", 625, 571, 104, 52),
        ("Desk 5", 729, 518, 47, 105),
        ("Desk 9", 896, 569, 51, 104),
        ("Desk 10", 948, 569, 51, 104),
        ("Desk 7", 1057, 382, 51, 104),
        ("Desk 8", 1110, 382, 51, 104),
        ("Desk 6", 898, 390, 51, 104),
        ("Desk 11", 1103, 570, 51, 104),
        ("Desk 12", 1155, 570, 51, 104),
        ("Desk 13", 1815, 353, 51, 104),
        ("Desk 14", 1985, 435, 51, 104),
        ("Desk 15", 1933, 541, 104, 52),
        ("Desk 16", 1933, 626, 104, 52),
    ]

    # Inserisci solo se non esiste già uno space con quel nome in quella location
    for name, x, y, width, height in spaces_data:
        exists = (
            db.query(Space)
            .filter(Space.location_id == location.id, Space.name == name)
            .first()
        )
        if exists:
            continue

        space = Space(
            organization_id=org_id,
            location_id=location.id,
            name=name,
            kind="desk",
            is_active=True,
            require_subject=True,
            x=x,
            y=y,
            width=width,
            height=height,
            rotation=0,
        )
        db.add(space)

    db.commit()