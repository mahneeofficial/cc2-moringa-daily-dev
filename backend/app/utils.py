from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from app.extensions import db

def role_required(*allowed_roles):
    """
    Decorator that checks if the cureent user's role is in the list of allowed_roles.
    Usage:
    @role_required("admin")
    @role_required("admin","tec_writer","user")
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args,**kwargs):
            from app.models import user
            user_id=get_jwt_identity()
            user=db.session.get(User, int(user_id))

            if not user:
                return jsonify({"error": "User not found"}), 404
            if user.role not in allowed_roles:
                return jsonify({"error": "Forbidden. Insufficient permissions."}),403
            return fn(*args,**kwargs)         
        return wrapper
    return decorator    
