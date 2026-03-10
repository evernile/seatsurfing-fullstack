from app.core.database import SessionLocal
from app.core.seed import seed_db


def main() -> None:
    db = SessionLocal()
    try:
        seed_db(db)
        print("✅ Seed completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()