"""Schema doctor — brings a database up to the current model schema.

Used by setup_db.py (CLI) and by create_app() on dev-server startup so a
developer who starts the backend directly with `python run.py` against an
old database still gets a working schema.

All operations are idempotent.
"""

from sqlalchemy import CheckConstraint, MetaData, Table, text

from app.extensions import db
from app.models import Content


PENDING_STATUS_CONSTRAINT = (
    '"Status" IN (\'Draft\', \'Pending\', \'Published\', \'Archived\')'
)


# Error signatures that mean "this database predates the current models"
SCHEMA_DRIFT_MARKERS = (
    "no such column",
    "has no column",
    "no column named",
    "check constraint",
    "duplicate column",
)


def looks_like_schema_drift(details):
    lowered = str(details).lower()
    return any(marker in lowered for marker in SCHEMA_DRIFT_MARKERS)


def schema_drift_hint():
    return (
        "The database schema is out of date. Run `bash dev.sh` "
        "(or `cd backend && python setup_db.py`) to repair it, then try again."
    )


def _table_names(engine):
    return set(db.inspect(engine).get_table_names())


def database_is_empty(engine):
    return len(_table_names(engine)) == 0


def add_missing_columns(engine):
    """ALTER TABLE ... ADD COLUMN for every model column the DB is missing."""
    inspector = db.inspect(engine)
    existing_tables = set(inspector.get_table_names())
    preparer = engine.dialect.identifier_preparer
    added = []

    for table in db.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue

        existing_cols = {c["name"] for c in inspector.get_columns(table.name)}

        for col in table.columns:
            if col.name in existing_cols:
                continue

            col_type = col.type.compile(engine.dialect)
            quoted = f"{table.name}.{col.name}"

            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"ALTER TABLE {preparer.quote(table.name)} "
                        f"ADD COLUMN {preparer.quote(col.name)} {col_type}"
                    )
                )

            added.append(quoted)

    return added


def _rebuild_content_table_sqlite(engine):
    """Recreate `content` from the model definition.

    SQLite cannot alter constraints in place, so the table is rebuilt.
    Existing rows are copied into the new table.
    """
    import sqlite3

    from sqlalchemy.schema import CreateTable

    inspector = db.inspect(engine)
    old_cols = {c["name"] for c in inspector.get_columns("content")}

    scratch = MetaData(naming_convention=db.metadata.naming_convention)
    new_table = Table("content_rebuild", scratch)

    for col in Content.__table__.columns:
        new_table.append_column(col._copy())

    for constraint in Content.__table__.constraints:
        if isinstance(constraint, CheckConstraint):
            new_table.append_constraint(constraint._copy())

    preparer = engine.dialect.identifier_preparer

    common = [
        c.name
        for c in new_table.columns
        if c.name in old_cols
    ]

    common_quoted = ", ".join(
        preparer.quote(c) for c in common
    )

    create_ddl = str(CreateTable(new_table).compile(engine))

    insert_sql = (
        f"INSERT INTO content_rebuild ({common_quoted}) "
        f"SELECT {common_quoted} FROM content"
    )

    engine.dispose()

    conn = sqlite3.connect(engine.url.database)

    try:
        conn.isolation_level = None
        cur = conn.cursor()

        cur.execute("PRAGMA foreign_keys=OFF")
        cur.execute("PRAGMA legacy_alter_table=ON")

        cur.execute("BEGIN")
        cur.execute(create_ddl)
        cur.execute(insert_sql)
        cur.execute("DROP TABLE content")
        cur.execute("ALTER TABLE content_rebuild RENAME TO content")
        cur.execute("COMMIT")

        cur.execute("PRAGMA legacy_alter_table=OFF")
        cur.execute("PRAGMA foreign_keys=ON")

        issues = cur.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if issues:
            print(
                f"⚠ foreign_key_check reported {len(issues)} issue(s) "
                "— review them before deploying."
            )

        cur.close()

    finally:
        conn.close()


def fix_content_status_constraint(engine):
    """Make sure the content status constraint allows 'Pending'."""

    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            ddl = conn.execute(
                text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type='table' AND name='content'"
                )
            ).scalar()

        if ddl and "Pending" not in ddl:
            _rebuild_content_table_sqlite(engine)
            return True

        return False

    # Postgres & friends: swap the constraint directly (best effort)
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE content DROP CONSTRAINT IF EXISTS check_valid_content_status"
            ))
            conn.execute(text(
                f"ALTER TABLE content ADD CONSTRAINT check_valid_content_status "
                f"CHECK ({PENDING_STATUS_CONSTRAINT})"
            ))
        return True

    except Exception as exc:
        print(
            f"⚠ could not update the status constraint: {exc}"
        )
        return False


def repair_schema(engine, verbose=True):
    """Bring an existing database up to the current model schema."""

    db.create_all()

    added = add_missing_columns(engine)
    constraint_fixed = fix_content_status_constraint(engine)

    if verbose:
        for col in added:
            print(f"  ✓ added missing column {col}")

        if constraint_fixed:
            print(
                "  ✓ content status constraint now allows 'Pending'"
            )

        if not added and not constraint_fixed:
            print("  ✓ schema already up to date.")

    return bool(added or constraint_fixed)


def check_and_repair(app, verbose=True):
    """Entry point used at app start: quietly repair drift if detected."""
    with app.app_context():
        engine = db.engine

        if database_is_empty(engine):
            return False  # nothing to repair yet (fresh DB, create_all handles it)
        return repair_schema(engine, verbose=verbose)
