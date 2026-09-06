import os

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Profile, User

profiles_bp = Blueprint("profiles", __name__)

DEFAULT_AVATAR = "https://ui-avatars.com/api/?background=random&name="


def _current_user_id():
    """Extract integer user ID safely from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        if isinstance(identity, dict):
            return int(identity.get("id"))
        return int(identity)
    except (ValueError, TypeError):
        return None


def _absolute_media_url(url, request_host=None):
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = request_host or "http://127.0.0.1:5001"
    if not url.startswith("/"):
        url = f"/{url}"
    return f"{base}{url}"


def _format_profile_response(user, profile, host):
    """Format unified profile dictionary for public and private access."""
    avatar_url = profile.ProfileImage if profile else None
    if not avatar_url:
        avatar_url = f"{DEFAULT_AVATAR}{user.Username}"
    else:
        avatar_url = _absolute_media_url(avatar_url, host)

    bio = profile.Bio if profile else ""
    interests = getattr(profile, "Interests", "") if profile else ""

    return {
        "profile_id": profile.ProfileID if profile else None,
        "user_id": user.UserID,
        "username": user.Username,
        "email": user.Email,
        "bio": bio,
        "interests": interests,
        "profile_image": avatar_url,
        "role": user.Role,
        "is_admin": str(user.Role or "").lower() == "admin",
        "profile": {
            "profile_id": profile.ProfileID if profile else None,
            "bio": bio,
            "interests": interests,
            "profile_image": avatar_url,
        },
        "user": {
            "id": user.UserID,
            "username": user.Username,
            "email": user.Email,
            "role": user.Role,
        },
    }


# -------------------------------------------------------------------
# 1. GET CURRENT LOGGED-IN USER PROFILE
# -------------------------------------------------------------------
@profiles_bp.get("/me")
@jwt_required()
def get_profile():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token or user identity"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = Profile.query.filter_by(UserID=user_id).first()
    if not profile:
        profile = Profile(UserID=user_id)
        db.session.add(profile)
        db.session.commit()

    host = request.host_url.rstrip("/") if request else "http://127.0.0.1:5001"
    return jsonify(_format_profile_response(user, profile, host)), 200


# -------------------------------------------------------------------
# 2. GET PUBLIC PROFILE BY USER ID
# -------------------------------------------------------------------
@profiles_bp.get("/<int:user_id>")
def get_public_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = Profile.query.filter_by(UserID=user_id).first()
    host = request.host_url.rstrip("/") if request else "http://127.0.0.1:5001"
    return jsonify(_format_profile_response(user, profile, host)), 200


# -------------------------------------------------------------------
# 3. UPDATE PROFILE AND AVATAR PICTURE
# -------------------------------------------------------------------
@profiles_bp.put("/me")
@jwt_required()
def update_profile():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Invalid token or user identity"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = Profile.query.filter_by(UserID=user_id).first()
    if not profile:
        profile = Profile(UserID=user_id)
        db.session.add(profile)

    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    file = (
        request.files.get("file")
        or request.files.get("profile_image")
        or request.files.get("profile_picture")
        or request.files.get("avatar")
    )

    if "bio" in data:
        profile.Bio = data.get("bio")
    if "interests" in data and hasattr(profile, "Interests"):
        profile.Interests = data.get("interests")

    if file:
        filename = secure_filename(file.filename)
        if filename:
            upload_dir = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            profile.ProfileImage = f"/static/uploads/{filename}"
    elif "profile_image" in data or "profileImage" in data:
        profile.ProfileImage = data.get("profile_image") or data.get("profileImage")

    db.session.commit()

    host = request.host_url.rstrip("/") if request else "http://127.0.0.1:5001"
    res_data = _format_profile_response(user, profile, host)
    res_data["message"] = "Profile updated successfully."
    return jsonify(res_data), 200