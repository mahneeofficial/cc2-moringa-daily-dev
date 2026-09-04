from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Category
from app.utils import role_required

categories_bp = Blueprint("categories", __name__)


def safe_get_user_id():
    """Safely extract integer user ID from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


# -------------------------------------------------------------------
# 1. LIST ALL CATEGORIES
# -------------------------------------------------------------------
@categories_bp.get("")
def list_categories():
    """List all categories
    ---
    tags:
      - Categories
    responses:
      200:
        description: List of categories ordered alphabetically by name
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
                example: 1
              category_id:
                type: integer
                example: 1
              name:
                type: string
                example: Web Development
              description:
                type: string
                example: Articles related to frontend and backend development.
      500:
        description: Database query or server error
    """
    try:
        categories = Category.query.order_by(Category.Name.asc()).all()
        return (
            jsonify([
                {
                    "id": cat.CategoryID,
                    "category_id": cat.CategoryID,
                    "name": cat.Name,
                    "description": cat.Description,
                }
                for cat in categories
            ]),
            200,
        )
    except Exception as e:
        return (
            jsonify({"error": "Failed to fetch categories", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 2. GET SINGLE CATEGORY
# -------------------------------------------------------------------
@categories_bp.get("/<int:category_id>")
def get_category(category_id):
    """Get category by ID
    ---
    tags:
      - Categories
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID of the category to retrieve
    responses:
      200:
        description: Category details retrieved successfully
        schema:
          type: object
          properties:
            id:
              type: integer
              example: 1
            category_id:
              type: integer
              example: 1
            name:
              type: string
              example: Web Development
            description:
              type: string
              example: Articles related to frontend and backend development.
      404:
        description: Category not found
    """
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    return (
        jsonify({
            "id": category.CategoryID,
            "category_id": category.CategoryID,
            "name": category.Name,
            "description": category.Description,
        }),
        200,
    )


# -------------------------------------------------------------------
# 3. CREATE CATEGORY
# -------------------------------------------------------------------
@categories_bp.post("")
@jwt_required()
@role_required("Admin", "tech_writer")
def create_category():
    """Create a new category
    ---
    tags:
      - Categories
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
          properties:
            name:
              type: string
              example: DevOps
            description:
              type: string
              example: Continuous integration, deployment, and cloud infrastructure.
    responses:
      201:
        description: Category created successfully
      400:
        description: Missing required field or invalid user identity
      401:
        description: Unauthorized / Missing JWT token
      403:
        description: Forbidden / Role not permitted
      409:
        description: Category name already exists
      500:
        description: Database insertion error
    """
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = data.get("name")
    if not name or not str(name).strip():
        return jsonify({"error": "Category name is required."}), 400

    # Case-insensitive duplicate check
    existing_category = Category.query.filter(
        Category.Name.ilike(str(name).strip())
    ).first()
    if existing_category:
        return jsonify({"error": "Category already exists."}), 409

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    try:
        new_category = Category(
            Name=str(name).strip(),
            Description=data.get("description", ""),
            CreatedBy=user_id,
        )
        db.session.add(new_category)
        db.session.commit()

        return (
            jsonify({
                "id": new_category.CategoryID,
                "category_id": new_category.CategoryID,
                "name": new_category.Name,
                "description": new_category.Description,
                "message": "Category created successfully.",
            }),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to create category", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 4. UPDATE CATEGORY
# -------------------------------------------------------------------
@categories_bp.put("/<int:category_id>")
@jwt_required()
@role_required("Admin", "tech_writer")
def update_category(category_id):
    """Update an existing category
    ---
    tags:
      - Categories
    security:
      - BearerAuth: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID of the category to update
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            name:
              type: string
              example: Cloud Computing
            description:
              type: string
              example: Updated description for cloud technologies.
    responses:
      200:
        description: Category updated successfully
      401:
        description: Unauthorized / Missing JWT token
      403:
        description: Forbidden / Role not permitted
      404:
        description: Category not found
      409:
        description: Category name already in use by another category
      500:
        description: Database update error
    """
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    new_name = data.get("name")

    if new_name and str(new_name).strip():
        existing_category = Category.query.filter(
            Category.Name.ilike(str(new_name).strip()),
            Category.CategoryID != category.CategoryID,
        ).first()

        if existing_category:
            return (
                jsonify({"error": "Category with this name already exists"}),
                409,
            )

        category.Name = str(new_name).strip()

    if "description" in data:
        category.Description = data.get("description")

    try:
        db.session.commit()
        return (
            jsonify({
                "id": category.CategoryID,
                "category_id": category.CategoryID,
                "name": category.Name,
                "description": category.Description,
                "message": "Category updated successfully.",
            }),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to update category", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 5. DELETE CATEGORY
# -------------------------------------------------------------------
@categories_bp.delete("/<int:category_id>")
@jwt_required()
@role_required("Admin")
def delete_category(category_id):
    """Delete a category
    ---
    tags:
      - Categories
    security:
      - BearerAuth: []
    parameters:
      - name: category_id
        in: path
        type: integer
        required: true
        description: ID of the category to delete
    responses:
      200:
        description: Category deleted successfully
      401:
        description: Unauthorized / Missing JWT token
      403:
        description: Forbidden / Only Admins can delete categories
      404:
        description: Category not found
      500:
        description: Database deletion error
    """
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Category not found"}), 404

    try:
        db.session.delete(category)
        db.session.commit()
        return (
            jsonify({
                "message": "Category deleted successfully.",
                "category_id": category_id,
            }),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to delete category", "details": str(e)}),
            500,
        )