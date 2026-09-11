from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.utils import iso_utc
from app.extensions import db
from app.models import Category, Subscription

subscriptions_bp = Blueprint("subscriptions", __name__)


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity across all common JWT structures."""
    try:
        identity = get_jwt_identity()
        if identity is None:
            return None
        if isinstance(identity, dict):
            val = (
                identity.get("id")
                or identity.get("user_id")
                or identity.get("UserID")
                or identity.get("sub")
            )
            return int(val) if val is not None else None
        return int(identity)
    except (ValueError, TypeError):
        return None


# ------------------ SUBSCRIBE TO CATEGORY ------------------ #


@subscriptions_bp.post("")
@jwt_required()
def subscribe_to_category():
<<<<<<< HEAD
    """Subscribe to a specific category.
    ---
    tags:
      - Subscriptions
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - category_id
          properties:
            category_id:
              type: integer
              description: ID of the category to subscribe to
              example: 1
    responses:
      201:
        description: Subscribed successfully.
      400:
        description: Missing category_id or invalid user identity.
      401:
        description: Unauthorized.
      404:
        description: Category not found.
      409:
        description: Already subscribed to this category.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
=======
    user_id = safe_get_user_id()
    if not user_id:
>>>>>>> b967a37c7ac44c464ee1430f46bf1c288dbedd03
        return jsonify({"error": "Invalid user identity"}), 400

    data = request.get_json(silent=True) or {}
    category_id = data.get("category_id")

    if not category_id:
        return jsonify({"error": "category_id is required"}), 400

    # Verify category exists
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    # Check if already subscribed
    existing = Subscription.query.filter_by(
        UserID=user_id, CategoryID=category_id
    ).first()

    if existing:
        return (
            jsonify({"error": "You are already subscribed to this category"}),
            409,
        )

    subscription = Subscription(UserID=user_id, CategoryID=category_id)
    db.session.add(subscription)
    db.session.commit()

    return (
        jsonify({
            "message": "Subscribed successfully",
            "subscription_id": subscription.SubscriptionID,
            "category_id": category.CategoryID,
            "category_name": category.Name,
        }),
        201,
    )


# ------------------ GET MY SUBSCRIPTIONS ------------------ #


@subscriptions_bp.get("")
@jwt_required()
def get_my_subscriptions():
<<<<<<< HEAD
    """Get all subscriptions for the authenticated user.
    ---
    tags:
      - Subscriptions
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of active subscriptions retrieved successfully.
      400:
        description: Invalid user identity.
      401:
        description: Unauthorized.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
=======
    user_id = safe_get_user_id()
    if not user_id:
>>>>>>> b967a37c7ac44c464ee1430f46bf1c288dbedd03
        return jsonify({"error": "Invalid user identity"}), 400

    subscriptions = Subscription.query.filter_by(UserID=user_id).all()

    return (
        jsonify([
            {
                "subscription_id": sub.SubscriptionID,
                "category_id": sub.CategoryID,
                "category_name": getattr(sub.category, "Name", None)
                if hasattr(sub, "category")
                else None,
                "created_at": (
                    iso_utc(sub.CreatedAt) if sub.CreatedAt else None
                ),
            }
            for sub in subscriptions
        ]),
        200,
    )


# ------------------ UNSUBSCRIBE ------------------ #


@subscriptions_bp.delete("/<int:category_id>")
@jwt_required()
def unsubscribe_from_category(category_id):
<<<<<<< HEAD
    """Unsubscribe from a specific category.
    ---
    tags:
      - Subscriptions
    security:
      - BearerAuth: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID of the category to unsubscribe from
    responses:
      200:
        description: Unsubscribed successfully.
      400:
        description: Invalid user identity.
      401:
        description: Unauthorized.
      404:
        description: Subscription not found.
    """
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
=======
    user_id = safe_get_user_id()
    if not user_id:
>>>>>>> b967a37c7ac44c464ee1430f46bf1c288dbedd03
        return jsonify({"error": "Invalid user identity"}), 400

    subscription = Subscription.query.filter_by(
        UserID=user_id, CategoryID=category_id
    ).first()

    if not subscription:
        return (
            jsonify({"error": "You are not subscribed to this category."}),
            404,
        )

    db.session.delete(subscription)
    db.session.commit()

    return jsonify({"message": "Unsubscribed successfully"}), 200