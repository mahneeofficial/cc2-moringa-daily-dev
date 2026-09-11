from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Comment, Content, User
from app.utils import iso_utc

comments_bp = Blueprint("comments", __name__)


def safe_get_user_id():
    """Safely extract integer user ID from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(
            identity.get("id")
            or identity.get("user_id")
            or identity.get("UserID")
        )
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
@comments_bp.get("/content/<int:content_id>/comments")
def get_comments(content_id):
    """Get nested comment tree for a specific article or content item
    ---
    tags:
      - Comments
    parameters:
      - name: content_id
        in: path
        type: integer
        required: true
        description: ID of the content item whose comments to retrieve
    responses:
      200:
        description: List of top-level comments with recursively nested replies
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 10
              comment_id:
                type: integer
                example: 10
              content_id:
                type: integer
                example: 1
              user_id:
                type: integer
                example: 5
              parent_id:
                type: integer
                nullable: true
                example: null
              parent_comment_id:
                type: integer
                nullable: true
                example: null
              body:
                type: string
                example: Great article! Thanks for sharing.
              text:
                type: string
                example: Great article! Thanks for sharing.
              created_at:
                type: string
                example: "2026-03-31T14:30:00"
              created_at_formatted:
                type: string
                example: "31 Mar 2026 14:30"
              author:
                type: object
                properties:
                  id:
                    type: integer
                    example: 5
                  username:
                    type: string
                    example: john_doe
                  profile_image:
                    type: string
                    nullable: true
                    example: /static/uploads/avatars/avatar_user_5.png
              replies:
                type: array
                items:
                  type: object
      404:
        description: Content not found
    """
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
@comments_bp.post("/content/<int:content_id>/comments")
@jwt_required()
def add_comment(content_id):
    """Add a comment or reply to content
    ---
    tags:
      - Comments
    security:
      - BearerAuth: []
    parameters:
      - name: content_id
        in: path
        type: integer
        required: true
        description: ID of the content item to comment on
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - body
          properties:
            body:
              type: string
              example: This is a insightful perspective!
            text:
              type: string
              example: This is a insightful perspective!
            parent_id:
              type: integer
              description: Optional ID of the parent comment if replying to a comment
              example: 10
            parent_comment_id:
              type: integer
              description: Alternate field name for parent comment ID
              example: 10
    responses:
      201:
        description: Comment posted successfully
        schema:
          type: object
          properties:
            id:
              type: integer
              example: 11
            comment_id:
              type: integer
              example: 11
            content_id:
              type: integer
              example: 1
            body:
              type: string
              example: This is a insightful perspective!
            text:
              type: string
              example: This is a insightful perspective!
            parent_id:
              type: integer
              nullable: true
              example: 10
            parent_comment_id:
              type: integer
              nullable: true
              example: 10
            created_at:
              type: string
              example: "31 Mar 2026 14:35"
            author:
              type: object
              properties:
                id:
                  type: integer
                  example: 5
                username:
                  type: string
                  example: john_doe
                profile_image:
                  type: string
                  nullable: true
                  example: /static/uploads/avatars/avatar_user_5.png
            message:
              type: string
              example: Comment added successfully.
      400:
        description: Missing body text or parent comment content mismatch
      401:
        description: Unauthorized / Missing JWT token
      404:
        description: Content or parent comment not found
      500:
        description: Database insertion error
    """
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
# 3. MODIFY A COMMENT (PUT / PATCH)
# -------------------------------------------------------------------
def _handle_edit_comment(comment_id):
    """Core logic to edit an existing comment."""
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


@comments_bp.put("/comments/<int:comment_id>")
@jwt_required()
def edit_comment_put(comment_id):
    """Update a comment owned by current user (PUT)
    ---
    tags:
      - Comments
    security:
      - BearerAuth: []
    parameters:
      - name: comment_id
        in: path
        type: integer
        required: true
        description: ID of the comment to edit
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - body
          properties:
            body:
              type: string
              example: Updated comment text content.
            text:
              type: string
              example: Updated comment text content.
    responses:
      200:
        description: Comment updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Comment has been updated successfully
            id:
              type: integer
              example: 10
            body:
              type: string
              example: Updated comment text content.
            text:
              type: string
              example: Updated comment text content.
      400:
        description: Empty text or invalid user identity
      401:
        description: Unauthorized / Missing JWT token
      403:
        description: Forbidden / Cannot edit another user's comment
      404:
        description: Comment not found
      500:
        description: Database update error
    """
    return _handle_edit_comment(comment_id)


@comments_bp.patch("/comments/<int:comment_id>")
@jwt_required()
def edit_comment_patch(comment_id):
    """Partially update a comment owned by current user (PATCH)
    ---
    tags:
      - Comments
    security:
      - BearerAuth: []
    parameters:
      - name: comment_id
        in: path
        type: integer
        required: true
        description: ID of the comment to edit
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            body:
              type: string
              example: Updated comment text content.
            text:
              type: string
              example: Updated comment text content.
    responses:
      200:
        description: Comment updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Comment has been updated successfully
            id:
              type: integer
              example: 10
            body:
              type: string
              example: Updated comment text content.
            text:
              type: string
              example: Updated comment text content.
      400:
        description: Empty text or invalid user identity
      401:
        description: Unauthorized / Missing JWT token
      403:
        description: Forbidden / Cannot edit another user's comment
      404:
        description: Comment not found
      500:
        description: Database update error
    """
    return _handle_edit_comment(comment_id)


# -------------------------------------------------------------------
# 4. DELETE A COMMENT
# -------------------------------------------------------------------
@comments_bp.delete("/comments/<int:comment_id>")
@jwt_required()
def delete_comment(comment_id):
    """Delete a comment owned by current user
    ---
    tags:
      - Comments
    security:
      - BearerAuth: []
    parameters:
      - name: comment_id
        in: path
        type: integer
        required: true
        description: ID of the comment to delete
    responses:
      200:
        description: Comment deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Comment deleted successfully
      401:
        description: Unauthorized / Missing JWT token
      403:
        description: Forbidden / Cannot delete another user's comment
      404:
        description: Comment not found
      500:
        description: Database deletion error
    """
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    current_user = db.session.get(User, user_id)
    is_admin = bool(current_user and str(getattr(current_user, "Role", "")).lower() == "admin")

    if comment.UserID != user_id and not is_admin:
        return jsonify({"error": "You can only delete your own comments."}), 403

    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({"message": "Comment deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete comment", "details": str(e)}), 500