from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Content, Notification, Profile, User
from app.utils import role_required

admin_bp = Blueprint("admin", __name__)


# --------------------- CONTENT MODERATION --------------------- #

# Endpoint: GET /api/admin/pending-content
@admin_bp.get("/pending-content", strict_slashes=False)
@jwt_required()
@role_required("Admin", "admin")
def get_pending_content():
    pending_items = (
        Content.query.filter_by(Status="Pending")
        .order_by(Content.CreatedAt.desc())
        .all()
    )

    pending_data = [
        {
            "content_id": item.ContentID,
            "title": item.Title,
            "description": getattr(item, "Description", ""),
            "content_type": getattr(item, "ContentType", ""),
            "content_url": getattr(item, "ContentURL", ""),
            "duration": getattr(item, "Duration", None),
            "created_at": (
                item.CreatedAt.strftime("%d %b %Y") if item.CreatedAt else None
            ),
            "author": (
                item.author.Username if getattr(item, "author", None) else "Unknown"
            ),
        }
        for item in pending_items
    ]
    return jsonify(pending_data), 200


@admin_bp.patch("/content/<int:content_id>/status")
@jwt_required()
@role_required("Admin", "admin")
def update_content_status(content_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    reason = data.get("reason", "").strip()

    if new_status not in ["Published", "Rejected", "Pending", "Archived"]:
        return jsonify({"error": "Invalid status value."}), 400

    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found."}), 404

    content.Status = new_status

    if new_status == "Published":
        if hasattr(content, "IsApproved"):
            content.IsApproved = True
        if hasattr(content, "RejectionReason"):
            content.RejectionReason = None
        notif_msg = f"Your submission '{content.Title}' has been approved and published!"
    else:
        if hasattr(content, "IsApproved"):
            content.IsApproved = False
        if hasattr(content, "RejectionReason"):
            content.RejectionReason = reason or "No specific reason provided."
        notif_msg = f"Your submission '{content.Title}' status is now {new_status}. Reason: {reason or 'N/A'}"

    # Only create notification if content has an associated UserID
    if getattr(content, "UserID", None):
        new_notif = Notification(
            UserID=content.UserID,
            ContentID=content.ContentID,
            Message=notif_msg,
        )
        if hasattr(new_notif, "IsRead"):
            new_notif.IsRead = False
        db.session.add(new_notif)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database commit error: {str(e)}"}), 500

    return jsonify({"message": f"Content successfully marked as {new_status}."}), 200


# Endpoint: DELETE /api/admin/content/<int:content_id>
@admin_bp.delete("/content/<int:content_id>")
@jwt_required()
@role_required("Admin", "admin")
def delete_content(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found."}), 404

    # Remove associated notifications first to prevent foreign key constraint issues
    Notification.query.filter_by(ContentID=content_id).delete()

    db.session.delete(content)
    db.session.commit()

    return jsonify({"message": "Content deleted successfully."}), 200


# --------------------- USER MANAGEMENT --------------------- #

# Endpoint: GET /api/admin/users
@admin_bp.get("/users", strict_slashes=False)
@jwt_required()
@role_required("Admin", "admin")
def list_all_users():
    users = User.query.all()
    return (
        jsonify([
            {
                "id": user.UserID,
                "username": user.Username,
                "email": user.Email,
                "role": user.Role,
                "is_active": getattr(user, "IsActive", True),
            }
            for user in users
        ]),
        200,
    )


# Endpoint: POST /api/admin/users
@admin_bp.post("/users")
@jwt_required()
@role_required("Admin", "admin")
def admin_add_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "User")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required."}), 400

    existing = User.query.filter(
        (User.Username == username) | (User.Email == email)
    ).first()

    if existing:
        return jsonify({"error": "Username or email already exists."}), 409

    new_user = User(
        Username=username,
        Email=email,
        Role=role,
    )
    if hasattr(new_user, "IsActive"):
        new_user.IsActive = True

    # Securely hash password
    if hasattr(new_user, "set_password"):
        new_user.set_password(password)
    else:
        new_user.password_hash = password

    db.session.add(new_user)
    db.session.flush()

    db.session.add(Profile(UserID=new_user.UserID))
    db.session.commit()

    return (
        jsonify({"message": "User added successfully.", "user_id": new_user.UserID}),
        201,
    )


# Endpoint: PATCH /api/admin/users/<int:user_id>/status
@admin_bp.patch("/users/<int:user_id>/status")
@jwt_required()
@role_required("Admin", "admin")
def toggle_user_status(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    current_status = getattr(user, "IsActive", True)
    user.IsActive = not current_status
    db.session.commit()

    status_str = "activated" if user.IsActive else "deactivated"
    return jsonify({"message": f"User '{user.Username}' has been {status_str}."}), 200