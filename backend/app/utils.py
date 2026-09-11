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


def role_required(*roles):
    """Decorator to enforce role-based access control with casing-insensitive matching."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            if not identity:
                return jsonify({"error": "Unauthorized user"}), 401

            user_id = identity.get("id") or identity.get("UserID") if isinstance(identity, dict) else identity
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid user identity"}), 400

            user = db.session.get(User, user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404

            # Normalize roles: lowercase and replace spaces with underscores
            normalized_allowed = [str(r).lower().replace(" ", "_") for r in roles]
            user_role = str(user.Role).lower().replace(" ", "_") if user.Role else ""

            if user_role not in normalized_allowed:
                return jsonify({"error": "Forbidden: Insufficient permissions"}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator