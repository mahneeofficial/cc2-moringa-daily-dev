from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Comment, CommentReaction

comment_reactions_bp = Blueprint("comment_reactions", __name__)


def safe_get_user_id():
    """Safely extract integer user ID from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


def _get_reaction_counts(comment_id):
    """Utility to calculate total likes and dislikes for a comment."""
    likes = CommentReaction.query.filter_by(
        CommentID=comment_id, Reaction="like"
    ).count()
    dislikes = CommentReaction.query.filter_by(
        CommentID=comment_id, Reaction="dislike"
    ).count()
    return {"likes": likes, "dislikes": dislikes}


# -------------------------------------------------------------------
# 1. GET COMMENT REACTION SUMMARY
# -------------------------------------------------------------------
@comment_reactions_bp.get("/comments/<int:comment_id>/reactions")
@jwt_required(optional=True)
def get_comment_reactions(comment_id):
    """Get reaction counts and user reaction status for a comment
    ---
    tags:
      - Comment Reactions
    security:
      - BearerAuth: []
    parameters:
      - name: comment_id
        in: path
        type: integer
        required: true
        description: ID of the comment
    responses:
      200:
        description: Reaction summary retrieved successfully
        schema:
          type: object
          properties:
            comment_id:
              type: integer
              example: 42
            likes_count:
              type: integer
              example: 12
            dislikes_count:
              type: integer
              example: 1
            user_reaction:
              type: string
              nullable: true
              enum: [like, dislike, null]
              example: like
      404:
        description: Comment not found
    """
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    counts = _get_reaction_counts(comment_id)
    user_reaction = None

    try:
        user_id = safe_get_user_id()
        if user_id:
            existing = CommentReaction.query.filter_by(
                UserID=user_id, CommentID=comment_id
            ).first()
            if existing:
                user_reaction = existing.Reaction
    except (ValueError, TypeError):
        pass

    return (
        jsonify({
            "comment_id": comment_id,
            "likes_count": counts["likes"],
            "dislikes_count": counts["dislikes"],
            "user_reaction": user_reaction,
        }),
        200,
    )


# -------------------------------------------------------------------
# 2. REACT TO COMMENT (Add, Update, or Toggle)
# -------------------------------------------------------------------
@comment_reactions_bp.post("/comments/<int:comment_id>/reactions")
@jwt_required()
def react_to_comment(comment_id):
    """Add, update, or toggle a reaction on a comment
    ---
    tags:
      - Comment Reactions
    security:
      - BearerAuth: []
    parameters:
      - name: comment_id
        in: path
        type: integer
        required: true
        description: ID of the comment to react to
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            type:
              type: string
              enum: [like, dislike]
              example: like
            reaction:
              type: string
              enum: [like, dislike]
              example: like
            reaction_type:
              type: string
              enum: [like, dislike]
              example: like
    responses:
      200:
        description: Reaction recorded or toggled off successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Comment reaction recorded
            user_reaction:
              type: string
              nullable: true
              example: like
            likes_count:
              type: integer
              example: 13
            dislikes_count:
              type: integer
              example: 0
      400:
        description: Invalid reaction type or invalid user identity
      401:
        description: Unauthorized / Missing JWT token
      404:
        description: Comment not found
      500:
        description: Database transaction error
    """
    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    reaction_type = (
        data.get("type") or data.get("reaction") or data.get("reaction_type")
    )

    if reaction_type not in ("like", "dislike"):
        return (
            jsonify({"error": "Reaction type must be 'like' or 'dislike'."}),
            400,
        )

    try:
        existing = CommentReaction.query.filter_by(
            UserID=user_id, CommentID=comment_id
        ).first()

        if existing:
            if existing.Reaction == reaction_type:
                # Toggle off if same reaction sent twice
                db.session.delete(existing)
                db.session.commit()
                counts = _get_reaction_counts(comment_id)
                return (
                    jsonify({
                        "message": "Reaction removed",
                        "user_reaction": None,
                        "likes_count": counts["likes"],
                        "dislikes_count": counts["dislikes"],
                    }),
                    200,
                )

            existing.Reaction = reaction_type
        else:
            reaction = CommentReaction(
                UserID=user_id, CommentID=comment_id, Reaction=reaction_type
            )
            db.session.add(reaction)

        db.session.commit()
        counts = _get_reaction_counts(comment_id)

        return (
            jsonify({
                "message": "Comment reaction recorded",
                "user_reaction": reaction_type,
                "likes_count": counts["likes"],
                "dislikes_count": counts["dislikes"],
            }),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to record reaction", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 3. REMOVE COMMENT REACTION
# -------------------------------------------------------------------
@comment_reactions_bp.delete("/comments/<int:comment_id>/reactions")
@jwt_required()
def remove_comment_reaction(comment_id):
    """Explicitly remove an existing reaction from a comment
    ---
    tags:
      - Comment Reactions
    security:
      - BearerAuth: []
    parameters:
      - name: comment_id
        in: path
        type: integer
        required: true
        description: ID of the comment to remove reaction from
    responses:
      200:
        description: Reaction removed successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Comment reaction removed
            user_reaction:
              type: string
              nullable: true
              example: null
            likes_count:
              type: integer
              example: 12
            dislikes_count:
              type: integer
              example: 0
      400:
        description: Invalid user identity
      401:
        description: Unauthorized / Missing JWT token
      404:
        description: Comment or existing reaction not found
      500:
        description: Database deletion error
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    comment = db.session.get(Comment, comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    reaction = CommentReaction.query.filter_by(
        UserID=user_id, CommentID=comment_id
    ).first()

    if not reaction:
        return jsonify({"error": "Reaction not found"}), 404

    try:
        db.session.delete(reaction)
        db.session.commit()
        counts = _get_reaction_counts(comment_id)

        return (
            jsonify({
                "message": "Comment reaction removed",
                "user_reaction": None,
                "likes_count": counts["likes"],
                "dislikes_count": counts["dislikes"],
            }),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to remove reaction", "details": str(e)}),
            500,
        )