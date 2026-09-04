from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import User


def iso_utc(dt):
    """ISO-8601 string that JavaScript's Date parses as UTC.

    SQLite returns naive datetimes (stored as UTC). Without the 'Z' suffix,
    `new Date("2026-09-04T01:00:00")` is parsed as LOCAL time — in Nairobi
    (UTC+3) every brand-new post displayed as "3h ago". Appending 'Z' fixes
    relative-time rendering everywhere.
    """
    if not dt:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.isoformat()
    return dt.isoformat() + "Z"


def role_required(*allowed_roles):
    """Restrict an endpoint (already behind @jwt_required()) to certain roles.

    The JWT identity only stores the user id, so the role is looked up in the
    database. Matching is case-insensitive ("Admin" == "admin").
    """
    allowed = {str(r).lower() for r in allowed_roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()

            try:
                if isinstance(identity, dict):
                    user_id = int(identity.get("id"))
                else:
                    user_id = int(identity)
            except (TypeError, ValueError):
                return jsonify({"error": "Invalid or missing identity"}), 401

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"error": "User not found"}), 401

            user_role = str(getattr(user, "Role", "user") or "user").lower()

            if user_role not in allowed:
                return jsonify({"error": "Unauthorized access for this role"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
