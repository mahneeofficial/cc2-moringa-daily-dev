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
    if isinstance(identity, dict):
        val = identity.get("id") or identity.get("UserID") or identity.get("user_id")
        return int(val) if val is not None else None
    return int(identity)


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
        return jsonify([
            {
                "id": cat.CategoryID,
                "category_id": cat.CategoryID,
                "name": cat.Name,
                "description": getattr(cat, "Description", ""),
            }
            for cat in categories
        ]), 200
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

    return jsonify({
        "id": category.CategoryID,
        "category_id": category.CategoryID,
        "name": category.Name,
        "description": getattr(category, "Description", ""),
    }), 200


# -------------------------------------------------------------------
# 3. CREATE CATEGORY (ADMIN & TECH WRITER)
# -------------------------------------------------------------------
@categories_bp.route("", methods=["POST"], strict_slashes=False)
@categories_bp.route("/", methods=["POST"], strict_slashes=False)
@jwt_required()
@role_required("Admin", "Tech Writer", "tech_writer", "admin")
def create_category():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = data.get("name") or data.get("Name")
    description = data.get("description") or data.get("Description") or ""

    if not name or not str(name).strip():
        return jsonify({"error": "Category name is required."}), 400

    existing_category = Category.query.filter(
        Category.Name.ilike(str(name).strip())
    ).first()

    if existing_category:
        return jsonify({"error": "Category already exists."}), 409

    try:
        new_category = Category(
            Name=str(name).strip(),
            Description=description,
        )
        db.session.add(new_category)
        db.session.commit()

        return jsonify({
            "message": "Category created successfully.",
            "category": {
                "id": new_category.CategoryID,
                "category_id": new_category.CategoryID,
                "name": new_category.Name,
                "description": new_category.Description,
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create category", "details": str(e)}), 500