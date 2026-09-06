from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Notification
from app.utils import iso_utc, safe_get_user_id

notifications_bp = Blueprint("notifications", __name__)


# -------------------------------------------------------------------
# HELPER FUNCTIONS FOR EXTERNAL BLUEPRINTS
# -------------------------------------------------------------------
def create_notification(user_id, message, content_id=None, notification_type="general"):
    """Insert a system notification for a specific user."""
    if not user_id:
        return None
    try:
        notif = Notification(
            UserID=int(user_id),
            Message=message,
            ContentID=content_id,
            Type=notification_type,
            IsRead=False,
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception:
        db.session.rollback()
        return None


def notify_signup(user_id, username):
    """Triggered when a new user registers."""
    msg = f"Welcome to the portal, {username}! Your account has been successfully created."
    return create_notification(user_id, msg, notification_type="general")


def notify_login(user_id, username):
    """Triggered on successful user login."""
    msg = f"Welcome back, {username}! You have successfully logged in."
    return create_notification(user_id, msg, notification_type="general")


def notify_submission(user_id, content_id, title):
    """Triggered when a user submits a post for admin review."""
    msg = f"Your post '{title}' has been submitted and is currently pending admin review."
    return create_notification(user_id, msg, content_id=content_id, notification_type="report_received")


# Alias for backward compatibility across route imports
notify_post_submission = notify_submission


def notify_approval(user_id, content_id, title):
    """Triggered when an admin approves a post."""
    msg = f"Great news! Your post '{title}' has been approved and published to the public feed."
    return create_notification(user_id, msg, content_id=content_id, notification_type="report_resolved")


def notify_rejection(user_id, content_id, title, reason=None):
    """Triggered when an admin rejects a post with a reason."""
    reason_str = reason if reason else "No specific reason provided."
    msg = f"Your post '{title}' was rejected by the moderation team. Reason: {reason_str}"
    return create_notification(user_id, msg, content_id=content_id, notification_type="content_removed")


# -------------------------------------------------------------------
# INTERNAL ROUTE SERIALIZER
# -------------------------------------------------------------------
def _serialize(n):
    is_read = bool(getattr(n, "IsRead", False))
    created_at = (
        iso_utc(n.CreatedAt) if getattr(n, "CreatedAt", None) else None
    )
    content_id = getattr(n, "ContentID", None)
    notif_type = getattr(n, "Type", None) or "general"
    
    return {
        "id": n.NotificationID,
        "notification_id": n.NotificationID,
        "message": n.Message,
        "type": notif_type,
        "isRead": is_read,
        "is_read": is_read,
        "contentId": content_id,
        "content_id": content_id,
        "createdAt": created_at,
        "created_at": created_at,
    }


# -------------------------------------------------------------------
# ENDPOINTS
# -------------------------------------------------------------------
@notifications_bp.route("", methods=["GET", "OPTIONS"], strict_slashes=False)
@notifications_bp.route("/", methods=["GET", "OPTIONS"], strict_slashes=False)
@jwt_required(optional=True)
def get_notifications():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Invalid user identity"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user identity"}), 400

    notifications = (
        Notification.query.filter_by(UserID=user_id)
        .order_by(Notification.NotificationID.desc())
        .all()
    )

    return jsonify([_serialize(n) for n in notifications]), 200


@notifications_bp.route("/unread-count", methods=["GET", "OPTIONS"], strict_slashes=False)
@jwt_required(optional=True)
def unread_count():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Invalid user identity"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user identity"}), 400

    count = Notification.query.filter_by(
        UserID=user_id, IsRead=False
    ).count()
    return jsonify({"count": count, "unreadCount": count}), 200


@notifications_bp.route("/<int:notification_id>/read", methods=["PATCH", "PUT", "OPTIONS"], strict_slashes=False)
@jwt_required(optional=True)
def mark_notification_read(notification_id):
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Invalid user identity"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user identity"}), 400

    notification = db.session.get(Notification, notification_id)
    if not notification or notification.UserID != user_id:
        return jsonify({"error": "Notification not found"}), 404

    notification.IsRead = True
    db.session.commit()

    return jsonify(
        {
            "message": "Notification marked as read.",
            **_serialize(notification),
        }
    ), 200


@notifications_bp.route("/read-all", methods=["PATCH", "PUT", "OPTIONS"], strict_slashes=False)
@notifications_bp.route("/read_all", methods=["PATCH", "PUT", "OPTIONS"], strict_slashes=False)
@jwt_required(optional=True)
def mark_all_notifications_read():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Invalid user identity"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user identity"}), 400

    updated = (
        Notification.query.filter_by(UserID=user_id, IsRead=False).update(
            {"IsRead": True}
        )
    )
    db.session.commit()

    return jsonify(
        {
            "message": "All notifications marked as read.",
            "updated": updated,
        }
    ), 200


@notifications_bp.route("/<int:notification_id>", methods=["DELETE", "OPTIONS"], strict_slashes=False)
@jwt_required(optional=True)
def delete_notification(notification_id):
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Invalid user identity"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user identity"}), 400

    notification = db.session.get(Notification, notification_id)
    if not notification or notification.UserID != user_id:
        return jsonify({"error": "Notification not found"}), 404

    db.session.delete(notification)
    db.session.commit()

    return jsonify({"message": "Notification deleted", "id": notification_id}), 200


@notifications_bp.route("/clear-all", methods=["DELETE", "OPTIONS"], strict_slashes=False)
@notifications_bp.route("/clear_all", methods=["DELETE", "OPTIONS"], strict_slashes=False)
@jwt_required(optional=True)
def clear_all_notifications():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Invalid user identity"}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid user identity"}), 400

    count = Notification.query.filter_by(UserID=user_id).delete()
    db.session.commit()

    return jsonify({"message": "All notifications cleared", "count": count}), 200