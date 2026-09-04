from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.utils import iso_utc

from app.extensions import db
from app.models import (
    Content,
    ContentReaction,
    Notification,
    Share,
    User,
    Wishlist,
)


interactions_bp = Blueprint("interactions", __name__)


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


def _reaction_summary(content_id, user_id=None):
    """Return like/dislike counts + the current user's reaction."""
    likes = ContentReaction.query.filter_by(
        ContentID=content_id, Reaction="like"
    ).count()
    dislikes = ContentReaction.query.filter_by(
        ContentID=content_id, Reaction="dislike"
    ).count()

    user_reaction = None
    if user_id:
        reaction = ContentReaction.query.filter_by(
            ContentID=content_id, UserID=user_id
        ).first()
        if reaction:
            user_reaction = reaction.Reaction

    return {
        "likes": likes,
        "dislikes": dislikes,
        "userReaction": user_reaction,
        # snake_case duplicates so both frontend styles work
        "likes_count": likes,
        "dislikes_count": dislikes,
        "user_reaction": user_reaction,
    }


# ==========================================
# 1. CONTENT LIKES & REACTIONS
# ==========================================

@interactions_bp.patch("/posts/<int:post_id>/like")
@jwt_required()
def toggle_like(post_id):
    """Toggle like or unlike on a post/content item.
    ---
    tags:
      - Interactions
    security:
      - BearerAuth: []
    parameters:
      - name: post_id
        in: path
        type: integer
        required: true
        description: ID of the content post
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            liked:
              type: boolean
              default: true
              description: Set to true to like, false to unlike
    responses:
      200:
        description: Like status updated successfully.
      400:
        description: Invalid user identity.
      404:
        description: Content or User not found.
      500:
        description: Failed to update like status.
    """
    content = db.session.get(Content, post_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    try:
        current_user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    current_user = db.session.get(User, current_user_id)
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    liked = data.get("liked", True)

    try:
        existing_reaction = ContentReaction.query.filter_by(
            ContentID=post_id, UserID=current_user_id
        ).first()

        if liked:
            if not existing_reaction:
                new_reaction = ContentReaction(
                    ContentID=post_id, UserID=current_user_id, Reaction="like"
                )
                db.session.add(new_reaction)

                if content.UserID != current_user_id:
                    notification = Notification(
                        UserID=content.UserID,
                        ContentID=content.ContentID,
                        Message=f"{current_user.Username} liked your post: '{content.Title}'",
                    )
                    db.session.add(notification)
            elif existing_reaction.Reaction != "like":
                existing_reaction.Reaction = "like"
        else:
            if existing_reaction and existing_reaction.Reaction == "like":
                db.session.delete(existing_reaction)

        db.session.commit()

        actual_likes_count = ContentReaction.query.filter_by(
            ContentID=post_id, Reaction="like"
        ).count()

        if hasattr(content, "LikesCount"):
            content.LikesCount = actual_likes_count
            db.session.commit()

        is_liked = ContentReaction.query.filter_by(
            ContentID=post_id, UserID=current_user_id, Reaction="like"
        ).first() is not None
        comments_count = len(content.comments) if hasattr(content, "comments") else 0
        formatted_date = (
            content.CreatedAt.strftime("%d %b %Y") if content.CreatedAt else None
        )

        return jsonify({
            "content_id": content.ContentID,
            "content_type": content.ContentType,
            "content_url": content.ContentURL,
            "views_count": getattr(content, "ViewsCount", 0),
            "likes_count": actual_likes_count,
            "is_liked": is_liked,
            "comments_count": comments_count,
            "created_at": formatted_date,
            "title": content.Title,
            "description": content.Description,
            "status": content.Status,
            "author": {
                "username": (
                    content.author.Username if getattr(content, "author", None) else None
                ),
                "profile_image": (
                    content.author.profile.ProfileImage
                    if getattr(content, "author", None) and getattr(content.author, "profile", None)
                    else None
                ),
            },
            "categories": [
                {"id": cat.CategoryID, "name": cat.Name}
                for cat in getattr(content, "categories", [])
            ],
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update like status", "details": str(e)}), 500


# -------------------------------------------------------------------
# GET reaction summary (likes / dislikes / current user's reaction)
# -------------------------------------------------------------------
@interactions_bp.get("/content/<int:content_id>/reactions")
@jwt_required(optional=True)
def get_reaction_summary(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    try:
        user_id = safe_get_user_id()
    except Exception:
        user_id = None

    return jsonify(_reaction_summary(content_id, user_id)), 200


# -------------------------------------------------------------------
# POST a reaction ("like" / "dislike") — clicking the same reaction
# again toggles it off (Instagram-style).
# -------------------------------------------------------------------
@interactions_bp.post("/content/<int:content_id>/reactions")
@jwt_required()
def react_to_content(content_id):
    """React to content (like or dislike).
    ---
    tags:
      - Interactions
    security:
      - BearerAuth: []
    parameters:
      - name: content_id
        in: path
        type: integer
        required: true
        description: ID of the content item
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - reaction
          properties:
            reaction:
              type: string
              enum: [like, dislike]
              example: like
            type:
              type: string
              enum: [like, dislike]
    responses:
      200:
        description: Reaction recorded successfully.
      400:
        description: Missing or invalid reaction type.
      404:
        description: Content not found.
      500:
        description: Failed to record reaction.
    """
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    reaction_type = data.get("type") or data.get("reaction")
    if reaction_type not in ("like", "dislike"):
        return jsonify({"error": "Reaction type must be 'like' or 'dislike'."}), 400

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    try:
        existing = ContentReaction.query.filter_by(
            UserID=user_id, ContentID=content_id
        ).first()

        toggled_off = False
        if existing:
            if existing.Reaction == reaction_type:
                # Same reaction again -> remove it (toggle off)
                db.session.delete(existing)
                toggled_off = True
            else:
                existing.Reaction = reaction_type
        else:
            reaction = ContentReaction(
                UserID=user_id, ContentID=content_id, Reaction=reaction_type
            )
            db.session.add(reaction)

        # Notify the author when someone likes their content
        if reaction_type == "like" and not toggled_off and content.UserID != user_id:
            db.session.add(
                Notification(
                    UserID=content.UserID,
                    ContentID=content.ContentID,
                    Message=f"{current_user.Username} liked your post: '{content.Title}'",
                )
            )

        db.session.commit()

        if hasattr(content, "LikesCount"):
            content.LikesCount = ContentReaction.query.filter_by(
                ContentID=content_id, Reaction="like"
            ).count()
            db.session.commit()

        summary = _reaction_summary(content_id, user_id)
        summary["message"] = (
            "Reaction removed." if toggled_off else "Reaction recorded."
        )
        return jsonify(summary), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to record reaction", "details": str(e)}), 500


# ==========================================
# 2. SHARE
# ==========================================

@interactions_bp.post("/content/<int:content_id>/share")
@jwt_required()
def share_content(content_id):
    """Share content with another user.
    ---
    tags:
      - Interactions
    security:
      - BearerAuth: []
    parameters:
      - name: content_id
        in: path
        type: integer
        required: true
        description: ID of the content item to share
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - shared_with_user_id
          properties:
            shared_with_user_id:
              type: integer
              description: ID of the user to share content with
    responses:
      200:
        description: Share recorded successfully.
      400:
        description: Missing input data or shared_with_user_id.
      404:
        description: Content or Target user not found.
      500:
        description: Failed to record share.
    """
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No input data provided."}), 400

    shared_with_user_id = data.get("shared_with_user_id")
    if not shared_with_user_id:
        return jsonify({"error": "shared_with_user_id is required."}), 400

    target_user = db.session.get(User, shared_with_user_id)
    if not target_user:
        return jsonify({"error": "Target user not found"}), 404

    try:
        share = Share(
            UserID=safe_get_user_id(),
            ContentID=content_id,
            SharedWithUserID=shared_with_user_id,
        )
        db.session.add(share)
        db.session.commit()

        return jsonify({"message": "Share recorded."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to record share", "details": str(e)}), 500


# ==========================================
# 3. WISHLIST
# ==========================================

@interactions_bp.get("/users/me/wishlist")
@jwt_required()
def get_wishlist():
    """Get the current authenticated user's wishlist.
    ---
    tags:
      - Wishlist
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of wishlist items returned.
      401:
        description: Unauthorized.
    """
    user_id = safe_get_user_id()
    items = Wishlist.query.filter_by(UserID=user_id).all()

    return jsonify(
        [{"id": wishlist.WishlistID, "content_id": wishlist.ContentID} for wishlist in items]
    ), 200


@interactions_bp.post("/wishlist")
@jwt_required()
def add_to_wishlist():
    """Add a content item to the user's wishlist.
    ---
    tags:
      - Wishlist
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - content_id
          properties:
            content_id:
              type: integer
              description: ID of the content item
    responses:
      201:
        description: Added to wishlist successfully.
      400:
        description: Missing required content_id or input data.
      404:
        description: Content not found.
      409:
        description: Content is already in the wishlist.
      500:
        description: Failed to add to wishlist.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    content_id = data.get("content_id")
    if not content_id:
        return jsonify({"error": "content_id is required"}), 400

    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    user_id = safe_get_user_id()

    existing = Wishlist.query.filter_by(UserID=user_id, ContentID=content_id).first()
    if existing:
        return jsonify({"error": "Already in wishlist."}), 409

    try:
        wishlist = Wishlist(UserID=user_id, ContentID=content_id)
        db.session.add(wishlist)
        db.session.commit()
        return jsonify({"message": "Added to wishlist.", "id": wishlist.WishlistID}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add to wishlist", "details": str(e)}), 500


@interactions_bp.delete("/wishlist/<int:wishlist_id>")
@jwt_required()
def remove_from_wishlist(wishlist_id):
    """Remove an item from the user's wishlist.
    ---
    tags:
      - Wishlist
    security:
      - BearerAuth: []
    parameters:
      - name: wishlist_id
        in: path
        type: integer
        required: true
        description: ID of the wishlist record
    responses:
      200:
        description: Removed from wishlist successfully.
      403:
        description: Forbidden (Cannot delete another user's wishlist item).
      404:
        description: Wishlist item not found.
      500:
        description: Failed to remove from wishlist.
    """
    wishlist = db.session.get(Wishlist, wishlist_id)
    if not wishlist:
        return jsonify({"error": "Wishlist item not found"}), 404

    if wishlist.UserID != safe_get_user_id():
        return jsonify({"error": "Forbidden"}), 403

    try:
        db.session.delete(wishlist)
        db.session.commit()
        return jsonify({"message": "Removed from wishlist."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to remove from wishlist", "details": str(e)}), 500


# ==========================================
# 4. NOTIFICATIONS (legacy polling endpoint)
# ==========================================

@interactions_bp.get("/notifications")
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
        description: List of notifications returned.
      400:
        description: Invalid user identity.
    """
    try:
        current_user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    notifications = (
        Notification.query.filter_by(UserID=current_user_id)
        .order_by(Notification.NotificationID.desc())
        .all()
    )

    return jsonify(
        [
            {
                "id": n.NotificationID,
                "message": n.Message,
                "is_read": getattr(n, "IsRead", False),
                "isRead": getattr(n, "IsRead", False),
                "content_id": getattr(n, "ContentID", None),
                "contentId": getattr(n, "ContentID", None),
                "created_at": (
                    iso_utc(n.CreatedAt) if getattr(n, "CreatedAt", None) else None
                ),
                "createdAt": (
                    iso_utc(n.CreatedAt) if getattr(n, "CreatedAt", None) else None
                ),
            }
            for n in notifications
        ]
    ), 200
