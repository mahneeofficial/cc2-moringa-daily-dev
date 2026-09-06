from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import User


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity dict or scalar."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(
            identity.get("id")
            or identity.get("user_id")
            or identity.get("UserID")
        )
    return int(identity)


def iso_utc(dt):
    """ISO-8601 string that JavaScript's Date parses cleanly as UTC.

    Converts naive datetimes or tz-aware (+00:00) datetimes into
    a uniform 'YYYY-MM-DDTHH:MM:SSZ' string format.
    """
    if not dt:
        return None
    iso_str = dt.isoformat()
    if iso_str.endswith("+00:00"):
        return iso_str[:-6] + "Z"
    if not iso_str.endswith("Z") and getattr(dt, "tzinfo", None) is None:
        return iso_str + "Z"
    return iso_str


def role_required(*allowed_roles):
    """Restrict an endpoint (behind @jwt_required()) to specific user roles.

    Role comparisons are case-insensitive ("Admin" == "admin").
    """
    allowed = {str(r).lower() for r in allowed_roles}

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                user_id = safe_get_user_id()
                if not user_id:
                    return jsonify({"error": "Invalid or missing identity"}), 401
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