from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Profile, User

profiles_bp = Blueprint("profiles", __name__)


def _current_user_id():
    """JWT identity may be a plain string id or a dict with an id."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


@profiles_bp.get("/me")
@jwt_required()
def get_profile():
    user_id = _current_user_id()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = Profile.query.filter_by(UserID=user_id).first()
    if not profile:
        profile = Profile(UserID=user_id)
        db.session.add(profile)
        db.session.commit()

    return jsonify({
        "profile_id": profile.ProfileID,
        "user_id": profile.UserID,
        "username": user.Username,
        "email": user.Email,
        "bio": profile.Bio,
        "interests": profile.Interests,
        "skills": profile.Skills,
        "github_url": profile.GithubURL,
        # alias keys other frontend styles may use
        "github_profile": profile.GithubURL,
        "profile_image": profile.ProfileImage,
        "role": user.Role,
        "is_admin": str(user.Role or "").lower() == "admin",
        "profile": {
            "profile_id": profile.ProfileID,
            "bio": profile.Bio,
            "interests": profile.Interests,
            "skills": profile.Skills,
            "github_url": profile.GithubURL,
            "profile_image": profile.ProfileImage,
        },
        "user": {
            "id": user.UserID,
            "username": user.Username,
            "email": user.Email,
            "role": user.Role,
        },
    }), 200


@profiles_bp.put("/me")
@jwt_required()
def update_profile():
    # /me is always "your own profile" once identity comes from the JWT --
    # no separate ownership check needed, there's no other user_id to compare against.
    user_id = _current_user_id()
    profile = Profile.query.filter_by(UserID=user_id).first()
    if not profile:
        profile = Profile(UserID=user_id)
        db.session.add(profile)

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # Only overwrite fields the client actually sent, so a partial update
    # (e.g. only bio) can never blank out skills / github by accident.
    if "bio" in data:
        profile.Bio = data.get("bio")
    if "interests" in data:
        profile.Interests = data.get("interests")
    if "skills" in data or "tech_stack" in data:
        profile.Skills = data.get("skills") or data.get("tech_stack")
    if "github_url" in data or "github" in data or "github_profile" in data or "githubUrl" in data:
        profile.GithubURL = (
            data.get("github_url")
            or data.get("github")
            or data.get("github_profile")
            or data.get("githubUrl")
        )
    if "profile_image" in data or "profileImage" in data:
        profile.ProfileImage = data.get("profile_image") or data.get("profileImage")

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully.",
        "profile": {
            "profile_id": profile.ProfileID,
            "user_id": profile.UserID,
            "bio": profile.Bio,
            "interests": profile.Interests,
            "skills": profile.Skills,
            "github_url": profile.GithubURL,
            "profile_image": profile.ProfileImage,
        },
    }), 200
