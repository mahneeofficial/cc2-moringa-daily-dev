from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Content, Notification, Profile, User
from app.routes.notifications import notify_approval, notify_rejection
from app.utils import iso_utc, role_required

admin_bp = Blueprint("admin", __name__)


# --------------------- CONTENT MODERATION --------------------- #

@admin_bp.get("/pending-content", strict_slashes=False)
@jwt_required()
@role_required("Admin")
def get_pending_content():
    pending_items = (
        Content.query.filter_by(Status="Pending")
        .order_by(Content.CreatedAt.desc())
        .all()
    )

    pending_data = []
    for item in pending_items:
        author_username = (
            item.author.Username
            if getattr(item, "author", None)
            else "Anonymous"
        )

        profile_img = None
        if getattr(item, "author", None) and getattr(
            item.author, "profile", None
        ):
            profile_img = getattr(item.author.profile, "ProfileImage", None)

        categories = [
            {"id": cat.CategoryID, "name": cat.Name}
            for cat in getattr(item, "categories", [])
        ]

        pending_data.append(
            {
                "id": item.ContentID,
                "content_id": item.ContentID,
                "title": item.Title,
                "description": getattr(item, "Description", ""),
                "content_type": getattr(item, "ContentType", ""),
                "type": getattr(item, "ContentType", ""),
                "content_url": getattr(item, "ContentURL", ""),
                "url": getattr(item, "ContentURL", ""),
                "status": item.Status,
                "created_at": iso_utc(item.CreatedAt),
                "createdAt": iso_utc(item.CreatedAt),
                "author_id": item.UserID,
                "author": {
                    "username": author_username,
                    "profile_image": profile_img,
                },
                "author_username": author_username,
                "categories": categories,
                "category": categories[0] if categories else None,
            }
        )

    return jsonify(pending_data), 200


@admin_bp.patch("/content/<int:content_id>/status")
@jwt_required()
@role_required("Admin")
def update_content_status(content_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    reason = data.get("reason", "").strip()

    stored_status = "Archived" if new_status == "Rejected" else new_status

    if stored_status not in ["Published", "Archived", "Pending"]:
        return jsonify({"error": "Invalid status value."}), 400

    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found."}), 404

    was_pending = content.Status == "Pending"
    content.Status = stored_status

    if stored_status == "Published":
        content.IsApproved = True
        if hasattr(content, "RejectionReason"):
            content.RejectionReason = None
    else:
        content.IsApproved = False
        if hasattr(content, "RejectionReason"):
            content.RejectionReason = reason or "No specific reason provided."

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database commit error: {str(e)}"}), 500

    # Trigger user notifications via helper functions
    if getattr(content, "UserID", None):
        if stored_status == "Published":
            notify_approval(content.UserID, content.ContentID, content.Title)
        else:
            notify_rejection(
                content.UserID, content.ContentID, content.Title, reason
            )

    if stored_status == "Published" and was_pending:
        try:
            from app.routes.content import _notify_subscribers

            _notify_subscribers(content)
        except Exception:
            pass

    return (
        jsonify(
            {
                "message": f"Content successfully marked as {stored_status}.",
                "status": stored_status,
            }
        ),
        200,
    )


@admin_bp.delete("/content/<int:content_id>")
@jwt_required()
@role_required("Admin")
def delete_content(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found."}), 404

    Notification.query.filter_by(ContentID=content_id).delete()

    db.session.delete(content)
    db.session.commit()

    return jsonify({"message": "Content deleted successfully."}), 200


# --------------------- USER MANAGEMENT --------------------- #

@admin_bp.get("/users", strict_slashes=False)
@jwt_required()
@role_required("Admin")
def list_all_users():
    users = User.query.order_by(User.UserID.desc()).all()

    users_data = []
    for user in users:
        profile_img = (
            getattr(user.profile, "ProfileImage", None)
            if getattr(user, "profile", None)
            else None
        )
        bio = (
            getattr(user.profile, "Bio", "")
            if getattr(user, "profile", None)
            else ""
        )
        content_count = Content.query.filter_by(UserID=user.UserID).count()

        users_data.append(
            {
                "id": user.UserID,
                "user_id": user.UserID,
                "username": user.Username,
                "email": user.Email,
                "role": user.Role,
                "is_active": user.IsActive,
                "isActive": user.IsActive,
                "profile_image": profile_img,
                "bio": bio,
                "total_posts": content_count,
                "created_at": iso_utc(getattr(user, "CreatedAt", None)),
            }
        )

    return jsonify(users_data), 200


@admin_bp.post("/users")
@jwt_required()
@role_required("Admin")
def admin_add_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if role not in ("user", "tech_writer", "Admin"):
        role = "user"

    if not username or not email or not password:
        return (
            jsonify({"error": "Username, email, and password are required."}),
            400,
        )

    existing = User.query.filter(
        (User.Username == username) | (User.Email == email)
    ).first()

    if existing:
        return jsonify({"error": "Username or email already exists."}), 409

    new_user = User(
        Username=username,
        Email=email,
        Role=role,
        IsActive=True,
    )

    if hasattr(new_user, "set_password"):
        new_user.set_password(password)
    else:
        new_user.PasswordHash = generate_password_hash(password)

    db.session.add(new_user)
    db.session.flush()

    db.session.add(Profile(UserID=new_user.UserID))
    db.session.commit()

    return (
        jsonify(
            {
                "message": "User added successfully.",
                "user_id": new_user.UserID,
                "username": new_user.Username,
                "role": new_user.Role,
            }
        ),
        201,
    )


@admin_bp.patch("/users/<int:user_id>/status")
@jwt_required()
@role_required("Admin")
def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    user.IsActive = not user.IsActive
    db.session.commit()

    status_str = "activated" if user.IsActive else "deactivated"
    return (
        jsonify(
            {
                "message": f"User '{user.Username}' has been {status_str}.",
                "is_active": user.IsActive,
            }
        ),
        200,
    )