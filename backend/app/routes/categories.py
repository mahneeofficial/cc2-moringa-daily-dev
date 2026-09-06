from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Category, Subscription
from app.utils import role_required

categories_bp = Blueprint("categories", __name__)


def safe_get_user_id():
    """Safely extract integer user ID from JWT identity across all common JWT structures."""
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


def generate_slug(name):
    """Generate a clean URL slug from category name."""
    if not name:
        return ""
    return str(name).lower().replace("/", "-").replace(" ", "-")


def get_content_count(cat):
    """Retrieve database post/content count for a category."""
    if hasattr(cat, "contents"):
        try:
            return len(cat.contents)
        except TypeError:
            return cat.contents.count()
    elif hasattr(cat, "content"):
        try:
            return len(cat.content)
        except TypeError:
            return cat.content.count()
    return 0


# -------------------------------------------------------------------
# 1. LIST ALL CATEGORIES
# -------------------------------------------------------------------
@categories_bp.route("", methods=["GET"], strict_slashes=False)
@categories_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required(optional=True)
def list_categories():
    try:
        user_id = safe_get_user_id()
        subscribed_category_ids = set()

        if user_id:
            user_subs = Subscription.query.filter_by(UserID=user_id).all()
            subscribed_category_ids = {
                sub.CategoryID
                for sub in user_subs
                if getattr(sub, "CategoryID", None)
            }

        categories = Category.query.order_by(Category.Name.asc()).all()

        return jsonify(
            [
                {
                    "id": cat.CategoryID,
                    "category_id": cat.CategoryID,
                    "name": cat.Name,
                    "slug": getattr(cat, "Slug", None)
                    or generate_slug(cat.Name),
                    "description": cat.Description or "",
                    "contentCount": get_content_count(cat),
                    "content_count": get_content_count(cat),
                    "is_subscribed": cat.CategoryID in subscribed_category_ids,
                }
                for cat in categories
            ]
        ), 200
    except Exception as e:
        return jsonify(
            {"error": "Failed to fetch categories", "details": str(e)}
        ), 500


# -------------------------------------------------------------------
# 2. SUBSCRIBE / UNSUBSCRIBE ENDPOINTS
# -------------------------------------------------------------------
@categories_bp.route(
    "/<int:category_id>/subscribe", methods=["POST"], strict_slashes=False
)
@jwt_required()
def toggle_subscribe_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    user_id = safe_get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized user identity"}), 401

    try:
        existing_sub = Subscription.query.filter_by(
            UserID=user_id, CategoryID=category_id
        ).first()

        if existing_sub:
            db.session.delete(existing_sub)
            db.session.commit()
            return jsonify(
                {
                    "message": "Unsubscribed from category.",
                    "is_subscribed": False,
                    "category_id": category_id,
                }
            ), 200
        else:
            new_sub = Subscription(UserID=user_id, CategoryID=category_id)
            db.session.add(new_sub)
            db.session.commit()
            return jsonify(
                {
                    "message": "Subscribed to category.",
                    "is_subscribed": True,
                    "category_id": category_id,
                }
            ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": "Failed to toggle subscription", "details": str(e)}
        ), 500


@categories_bp.route(
    "/<int:category_id>/unsubscribe",
    methods=["DELETE", "POST"],
    strict_slashes=False,
)
@categories_bp.route(
    "/<int:category_id>/subscribe", methods=["DELETE"], strict_slashes=False
)
@jwt_required()
def explicit_unsubscribe_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    user_id = safe_get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized user identity"}), 401

    try:
        existing_sub = Subscription.query.filter_by(
            UserID=user_id, CategoryID=category_id
        ).first()

        if existing_sub:
            db.session.delete(existing_sub)
            db.session.commit()

        return jsonify(
            {
                "message": "Unsubscribed from category.",
                "is_subscribed": False,
                "category_id": category_id,
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": "Failed to unsubscribe", "details": str(e)}
        ), 500


# -------------------------------------------------------------------
# 3. GET SINGLE CATEGORY
# -------------------------------------------------------------------
@categories_bp.route(
    "/<int:category_id>", methods=["GET"], strict_slashes=False
)
def get_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    return jsonify(
        {
            "id": category.CategoryID,
            "category_id": category.CategoryID,
            "name": category.Name,
            "slug": getattr(category, "Slug", None)
            or generate_slug(category.Name),
            "description": category.Description or "",
            "contentCount": get_content_count(category),
            "content_count": get_content_count(category),
        }
    ), 200


# -------------------------------------------------------------------
# 4. CREATE CATEGORY
# -------------------------------------------------------------------
@categories_bp.route("", methods=["POST"], strict_slashes=False)
@categories_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
@role_required("Admin", "tech_writer")
def create_category():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = data.get("name")
    if not name or not str(name).strip():
        return jsonify({"error": "Category name is required."}), 400

    existing_category = Category.query.filter(
        Category.Name.ilike(str(name).strip())
    ).first()
    if existing_category:
        return jsonify({"error": "Category already exists."}), 409

    try:
        user_id = safe_get_user_id()
        new_category = Category(
            Name=str(name).strip(),
            Description=data.get("description", ""),
            CreatedBy=user_id,
        )
        db.session.add(new_category)
        db.session.commit()

        return jsonify(
            {
                "id": new_category.CategoryID,
                "category_id": new_category.CategoryID,
                "name": new_category.Name,
                "slug": generate_slug(new_category.Name),
                "description": new_category.Description,
                "contentCount": 0,
                "message": "Category created successfully.",
            }
        ), 201
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": "Failed to create category", "details": str(e)}
        ), 500


# -------------------------------------------------------------------
# 5. UPDATE CATEGORY (PUT/PATCH)
# -------------------------------------------------------------------
@categories_bp.route(
    "/<int:category_id>", methods=["PUT", "PATCH"], strict_slashes=False
)
@jwt_required()
@role_required("Admin", "tech_writer")
def update_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_name = data.get("name")

    if new_name and str(new_name).strip():
        existing_category = Category.query.filter(
            Category.Name.ilike(str(new_name).strip()),
            Category.CategoryID != category_id,
        ).first()

        if existing_category:
            return jsonify(
                {"error": "Category with this name already exists"}
            ), 409

        category.Name = str(new_name).strip()

    if "description" in data:
        category.Description = data.get("description")

    try:
        db.session.commit()
        return jsonify(
            {
                "id": category.CategoryID,
                "category_id": category.CategoryID,
                "name": category.Name,
                "slug": getattr(category, "Slug", None)
                or generate_slug(category.Name),
                "description": category.Description or "",
                "contentCount": get_content_count(category),
                "message": "Category updated successfully.",
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": "Failed to update category", "details": str(e)}
        ), 500


# -------------------------------------------------------------------
# 6. DELETE CATEGORY
# -------------------------------------------------------------------
@categories_bp.route(
    "/<int:category_id>", methods=["DELETE"], strict_slashes=False
)
@jwt_required()
@role_required("Admin")
def delete_category(category_id):
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify(
            {
                "message": "Category deleted successfully.",
                "category_id": category_id,
            }
        ), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(
            {"error": "Failed to delete category", "details": str(e)}
        ), 500