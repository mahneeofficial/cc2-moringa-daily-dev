from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Notification

notifications_bp = Blueprint("notifications", __name__)


def safe_get_user_id():
    """Safely extract integer user ID from JWT identity."""
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


# -------------------------------------------------------------------
# 1. GET ALL USER NOTIFICATIONS
# -------------------------------------------------------------------
@notifications_bp.get("")
@jwt_required()
def get_notifications():
    """Get all notifications for the current authenticated user.
    ---
    tags:
      - Notifications
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of notifications and unread count returned successfully.
      400:
        description: Invalid user identity.
      401:
        description: Unauthorized.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    notifs = (
        Notification.query.filter_by(UserID=user_id)
        .order_by(Notification.CreatedAt.desc())
        .all()
    )

    unread_count = sum(1 for n in notifs if not n.IsRead)

    return (
        jsonify(
            {
                "unread_count": unread_count,
                "notifications": [
                    {
                        "id": notification.NotificationID,
                        "notification_id": notification.NotificationID,
                        "message": notification.Message,
                        "is_read": notification.IsRead,
                        "content_id": getattr(notification, "ContentID", None),
                        "created_at": (
                            notification.CreatedAt.isoformat()
                            if notification.CreatedAt
                            else None
                        ),
                    }
                    for notification in notifs
                ],
            }
        ),
        200,
    )


# -------------------------------------------------------------------
# 2. MARK ALL NOTIFICATIONS AS READ
#    (Must be defined BEFORE /<int:notification_id> to avoid route conflict)
# -------------------------------------------------------------------
@notifications_bp.patch("/read-all")
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read for the current user.
    ---
    tags:
      - Notifications
    security:
      - BearerAuth: []
    responses:
      200:
        description: All unread notifications updated successfully.
      400:
        description: Invalid user identity.
      401:
        description: Unauthorized.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    # Bulk update for higher database efficiency
    updated_count = (
        Notification.query.filter_by(UserID=user_id, IsRead=False)
        .update({Notification.IsRead: True}, synchronize_session=False)
    )
    db.session.commit()

    return (
        jsonify(
            {
                "message": "All notifications marked as read.",
                "updated_count": updated_count,
            }
        ),
        200,
    )


# -------------------------------------------------------------------
# 3. MARK A SINGLE NOTIFICATION AS READ
# -------------------------------------------------------------------
@notifications_bp.patch("/<int:notification_id>/read")
@jwt_required()
def mark_as_read(notification_id):
    """Mark a single notification as read.
    ---
    tags:
      - Notifications
    security:
      - BearerAuth: []
    parameters:
      - name: notification_id
        in: path
        type: integer
        required: true
        description: ID of the notification to mark as read
    responses:
      200:
        description: Notification marked as read.
      400:
        description: Invalid user identity.
      403:
        description: Forbidden (Access denied to this notification).
      404:
        description: Notification not found.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    notif = db.session.get(Notification, notification_id)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404

    if notif.UserID != user_id:
        return jsonify({"error": "Forbidden: Access denied"}), 403

    notif.IsRead = True
    db.session.commit()

    return jsonify({"message": "Notification marked as read."}), 200


# -------------------------------------------------------------------
# 4. DELETE A NOTIFICATION
# -------------------------------------------------------------------
@notifications_bp.delete("/<int:notification_id>")
@jwt_required()
def delete_notification(notification_id):
    """Delete a single notification by ID.
    ---
    tags:
      - Notifications
    security:
      - BearerAuth: []
    parameters:
      - name: notification_id
        in: path
        type: integer
        required: true
        description: ID of the notification to delete
    responses:
      200:
        description: Notification deleted successfully.
      400:
        description: Invalid user identity.
      403:
        description: Forbidden (Access denied to this notification).
      404:
        description: Notification not found.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    notif = db.session.get(Notification, notification_id)
    if not notif:
        return jsonify({"error": "Notification not found"}), 404

    if notif.UserID != user_id:
        return jsonify({"error": "Forbidden: Access denied"}), 403

    db.session.delete(notif)
    db.session.commit()

    return jsonify({"message": "Notification deleted successfully."}), 200