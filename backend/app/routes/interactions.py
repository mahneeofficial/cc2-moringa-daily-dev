from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import (
    Bookmark,
    Content,
    ContentReaction,
    Notification,
    Share,
    User,
)
from app.utils import iso_utc

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
                        Type="like",
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
            "body": content.Body,
            "slug": content.Slug,
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
                {"id": cat.CategoryID, "name": cat.Name, "slug": cat.Slug}
                for cat in getattr(content, "categories", [])
            ],
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update like status", "details": str(e)}), 500


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


@interactions_bp.post("/content/<int:content_id>/reactions")
@jwt_required()
def react_to_content(content_id):
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
                db.session.delete(existing)
                toggled_off = True
            else:
                existing.Reaction = reaction_type
        else:
            reaction = ContentReaction(
                UserID=user_id, ContentID=content_id, Reaction=reaction_type
            )
            db.session.add(reaction)

        if reaction_type == "like" and not toggled_off and content.UserID != user_id:
            db.session.add(
                Notification(
                    UserID=content.UserID,
                    ContentID=content.ContentID,
                    Type="like",
                    Message=f"{current_user.Username} liked your post: '{content.Title}'",
                )
            )

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
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    data = request.get_json(silent=True) or {}
    shared_with_user_id = data.get("shared_with_user_id")

    if shared_with_user_id:
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

        return jsonify({"message": "Share recorded.", "share_id": share.ShareID}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to record share", "details": str(e)}), 500


# ==========================================
# 3. BOOKMARKS / WISHLIST
# ==========================================

@interactions_bp.get("/users/me/bookmarks")
@interactions_bp.get("/users/me/wishlist")
@jwt_required()
def get_bookmarks():
    user_id = safe_get_user_id()
    items = Bookmark.query.filter_by(UserID=user_id).order_by(Bookmark.BookmarkID.desc()).all()

    response = []
    for b in items:
        content = b.content
        if not content:
            continue

        comments_count = len(content.comments) if hasattr(content, "comments") else 0
        actual_likes_count = ContentReaction.query.filter_by(
            ContentID=content.ContentID, Reaction="like"
        ).count()
        is_liked = ContentReaction.query.filter_by(
            ContentID=content.ContentID, UserID=user_id, Reaction="like"
        ).first() is not None

        response.append({
            "id": b.BookmarkID,
            "bookmark_id": b.BookmarkID,
            "wishlist_id": b.BookmarkID,
            "content_id": content.ContentID,
            "content": {
                "id": content.ContentID,
                "content_id": content.ContentID,
                "title": content.Title,
                "slug": content.Slug,
                "description": content.Description,
                "body": content.Body,
                "content_type": content.ContentType,
                "content_url": content.ContentURL,
                "status": content.Status,
                "is_liked": is_liked,
                "is_bookmarked": True,
                "likes_count": actual_likes_count,
                "views_count": getattr(content, "ViewsCount", 0),
                "comments_count": comments_count,
                "created_at": iso_utc(content.CreatedAt) if content.CreatedAt else None,
                "author": {
                    "username": content.author.Username if getattr(content, "author", None) else None,
                    "profile_image": (
                        content.author.profile.ProfileImage
                        if getattr(content, "author", None) and getattr(content.author, "profile", None)
                        else None
                    ),
                },
                "categories": [
                    {"id": cat.CategoryID, "name": cat.Name, "slug": cat.Slug}
                    for cat in getattr(content, "categories", [])
                ],
            }
        })

    return jsonify(response), 200


@interactions_bp.post("/bookmarks")
@interactions_bp.post("/wishlist")
@jwt_required()
def add_to_bookmarks():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    content_id = data.get("content_id") or data.get("contentId") or data.get("ContentID")
    if not content_id:
        return jsonify({"error": "content_id is required"}), 400

    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    user_id = safe_get_user_id()

    existing = Bookmark.query.filter_by(UserID=user_id, ContentID=content_id).first()
    if existing:
        return jsonify({"message": "Already bookmarked.", "id": existing.BookmarkID}), 200

    try:
        bookmark = Bookmark(UserID=user_id, ContentID=content_id)
        db.session.add(bookmark)
        db.session.commit()
        return jsonify({"message": "Added to bookmarks.", "id": bookmark.BookmarkID}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add bookmark", "details": str(e)}), 500


@interactions_bp.delete("/bookmarks/<int:bookmark_id>")
@interactions_bp.delete("/wishlist/<int:bookmark_id>")
@jwt_required()
def remove_from_bookmarks(bookmark_id):
    user_id = safe_get_user_id()

    bookmark = db.session.get(Bookmark, bookmark_id)
    if not bookmark:
        bookmark = Bookmark.query.filter_by(UserID=user_id, ContentID=bookmark_id).first()

    if not bookmark:
        return jsonify({"error": "Bookmark item not found"}), 404

    if bookmark.UserID != user_id:
        return jsonify({"error": "Forbidden"}), 403

    try:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"message": "Removed from bookmarks."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to remove bookmark", "details": str(e)}), 500


# ==========================================
# 4. NOTIFICATIONS
# ==========================================

@interactions_bp.get("/notifications")
@jwt_required()
def get_notifications():
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
                "type": getattr(n, "Type", "general"),
                "message": n.Message,
                "is_read": getattr(n, "IsRead", False),
                "isRead": getattr(n, "IsRead", False),
                "content_id": getattr(n, "ContentID", None),
                "contentId": getattr(n, "ContentID", None),
                "created_at": iso_utc(n.CreatedAt) if getattr(n, "CreatedAt", None) else None,
                "createdAt": iso_utc(n.CreatedAt) if getattr(n, "CreatedAt", None) else None,
            }
            for n in notifications
        ]
    ), 200