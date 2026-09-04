from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils import iso_utc

from app.extensions import db
from app.models import Comment, Content, User

comments_bp = Blueprint("comments", __name__)


def safe_get_user_id():
    """Safely extract integer user ID from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


def _serialize_author(author):
    """Safely build author dictionary with profile image support."""
    if not author:
        return {"id": None, "username": "Unknown", "profile_image": None}

    profile_image = None
    if hasattr(author, "profile") and author.profile:
        profile_image = getattr(author.profile, "ProfileImage", None)

    return {
        "id": getattr(author, "UserID", None),
        "username": getattr(author, "Username", None),
        "profile_image": profile_image,
    }


def _build_comment_tree(comment):
    """Recursively serialize a comment and all its nested replies."""
    author_info = _serialize_author(getattr(comment, "author", None))
    created_at_iso = (
        iso_utc(comment.CreatedAt) if getattr(comment, "CreatedAt", None) else None
    )
    created_at_fmt = (
        comment.CreatedAt.strftime("%d %b %Y %H:%M")
        if getattr(comment, "CreatedAt", None)
        else None
    )

    return {
        "id": comment.CommentID,
        "comment_id": comment.CommentID,
        "content_id": comment.ContentID,
        "user_id": comment.UserID,
        "parent_id": comment.ParentCommentID,
        "parent_comment_id": comment.ParentCommentID,
        "body": comment.Text,
        "text": comment.Text,
        "created_at": created_at_iso or created_at_fmt,
        "createdAt": created_at_iso or created_at_fmt,
        "created_at_formatted": created_at_fmt,
        "user": author_info,
        "author": author_info,
        "replies": [
            _build_comment_tree(reply) for reply in getattr(comment, "replies", [])
        ],
    }


# -------------------------------------------------------------------
# 1. GET COMMENTS FOR CONTENT
# -------------------------------------------------------------------
@comments_bp.route(
    "/content/<int:content_id>/comments", methods=["GET"], strict_slashes=False
)
def get_comments(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    top_level = (
        Comment.query.filter_by(ContentID=content_id, ParentCommentID=None)
        .order_by(Comment.CreatedAt.asc())
        .all()
    )

    return jsonify([_build_comment_tree(comment) for comment in top_level]), 200


# -------------------------------------------------------------------
# 2. CREATE A COMMENT OR REPLY
# -------------------------------------------------------------------
@comments_bp.route(
    "/content/<int:content_id>/comments", methods=["POST"], strict_slashes=False
)
@jwt_required()
def add_comment(content_id):
    content = db.session.get(Content, content_id)
    if not content:
        return jsonify({"error": "Content not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    text = data.get("body") or data.get("text")
    parent_id = data.get("parent_id") or data.get("parent_comment_id")

    if not text or not str(text).strip():
        return jsonify({"error": "Comment body/text is required"}), 400

    if parent_id:
        parent_comment = db.session.get(Comment, parent_id)
        if not parent_comment:
            return jsonify({"error": "Parent comment not found"}), 404
        if parent_comment.ContentID != content_id:
            return jsonify({"error": "Parent comment belongs to different content"}), 400

    new_comment = Comment(
        Text=str(text).strip(),
        ContentID=content_id,
        UserID=user_id,
        ParentCommentID=parent_id,
    )

    try:
        db.session.add(new_comment)
        db.session.commit()

        author_info = _serialize_author(new_comment.author)
        created_at_iso = (
            iso_utc(new_comment.CreatedAt) if new_comment.CreatedAt else None
        )
        created_at_fmt = (
            new_comment.CreatedAt.strftime("%d %b %Y %H:%M")
            if new_comment.CreatedAt
            else None
        )

        return (
            jsonify(
                {
                    "id": new_comment.CommentID,
                    "comment_id": new_comment.CommentID,
                    "content_id": new_comment.ContentID,
                    "body": new_comment.Text,
                    "text": new_comment.Text,
                    "parent_id": new_comment.ParentCommentID,
                    "parent_comment_id": new_comment.ParentCommentID,
                    "created_at": created_at_iso or created_at_fmt,
                    "createdAt": created_at_iso or created_at_fmt,
                    "created_at_formatted": created_at_fmt,
                    "user": author_info,
                    "author": author_info,
                    "message": "Comment added successfully.",
                }
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to post comment", "details": str(e)}), 500


# -------------------------------------------------------------------
# 3. MODIFY A COMMENT
# -------------------------------------------------------------------
@comments_bp.route(
    "/comments/<int:comment_id>", methods=["PUT", "PATCH"], strict_slashes=False
)
@jwt_required()
def edit_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    if comment.UserID != user_id:
        return jsonify({"error": "You can only edit your own comments"}), 403

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_text = data.get("body") or data.get("text")

    if not new_text or not str(new_text).strip():
        return jsonify({"error": "Updated body/text is required"}), 400

    try:
        comment.Text = str(new_text).strip()
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Comment has been updated successfully",
                    "id": comment.CommentID,
                    "body": comment.Text,
                    "text": comment.Text,
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update comment", "details": str(e)}), 500


# -------------------------------------------------------------------
# 4. DELETE A COMMENT
# -------------------------------------------------------------------
@comments_bp.route(
    "/comments/<int:comment_id>", methods=["DELETE"], strict_slashes=False
)
@jwt_required()
def delete_comment(comment_id):
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    if comment.UserID != user_id:
        return jsonify({"error": "You can only delete your own comments."}), 403

    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"message": "Comment deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete comment", "details": str(e)}), 500