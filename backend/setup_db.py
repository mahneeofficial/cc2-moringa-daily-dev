"""Safe database setup & repair — works for fresh clones AND old databases.

Databases created from the previous models are missing columns the code now
uses (content.Summary / Duration / LikesCount / RejectionReason, users.is_admin)
and their `content` status check-constraint doesn't allow 'Pending', which made
every new learner post fail with a 500. Plain `flask db upgrade` can't fix an
unstamped (create_all-created) database, so this script repairs the schema
directly (see app/schema_doctor.py).

Everything is idempotent — run it as many times as you like. Existing data is
preserved. On first run with an empty database it also seeds default categories
and an admin account.

Run from the backend/ folder:  python setup_db.py
"""
from flask_migrate import stamp, upgrade

from app import create_app
from app.extensions import db
from app.models import Category, Profile, User
from app.schema_doctor import repair_schema
from sqlalchemy import text

DEFAULT_CATEGORIES = [
    "Software Engineering",
    "Data Science",
    "Cybersecurity",
    "DevOps",
    "Fullstack",
    "Frontend",
    "Backend",
    "Mobile",
    "Career",
    "AI/ML",
]

ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@moringa.com"
ADMIN_PASSWORD = "Admin123!"


def _table_names(engine):
    from app.schema_doctor import _table_names as _names
    return _names(engine)


def main():
    # FLASK_ENV=production on Render; defaults to development locally
    import os
    config_name = os.environ.get("FLASK_ENV", "development")
    app = create_app(config_name)

    with app.app_context():
        engine = db.engine

        if len(_table_names(engine)) == 0:
            print("→ No database found — creating tables from models…")
            db.create_all()
            stamp(revision="head")
            print("✓ Database created and stamped at the latest migration.")
        else:
            if "alembic_version" in _table_names(engine):
                print("→ Existing database — applying pending migrations…")
                try:
                    upgrade()
                    print("✓ Migrations up to date.")
                except Exception as exc:
                    print(f"⚠ migration step failed ({exc}) — "
                          "falling back to schema repair…")
            else:
                print("→ Existing database (no migration history) — "
                      "repairing schema directly…")

            print("→ Repairing schema (idempotent)…")
            repair_schema(engine)

            stamp(revision="head")

    # ---- First-run seed: categories + admin ----
    with app.app_context():
        seeded = False

        if Category.query.count() == 0:
            for name in DEFAULT_CATEGORIES:
                db.session.add(Category(Name=name, Description=f"{name} content"))
            db.session.commit()
            print(f"✓ Seeded {len(DEFAULT_CATEGORIES)} default categories.")
            seeded = True

        if User.query.count() == 0:
            admin = User(
                Username=ADMIN_USERNAME,
                Email=ADMIN_EMAIL,
                Role="Admin",
                IsActive=True,
                is_admin=True,
            )
            admin.password_hash = ADMIN_PASSWORD
            db.session.add(admin)
            db.session.flush()  # assigns admin.UserID
            db.session.add(Profile(UserID=admin.UserID))
            db.session.commit()
            print("✓ Seeded default admin account:")
            print(f"    username: {ADMIN_USERNAME}")
            print(f"    password: {ADMIN_PASSWORD}")
            seeded = True

        if not seeded:
            print("✓ Data already present — nothing to seed.")


if __name__ == "__main__":
    main()
