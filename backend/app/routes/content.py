import os
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Category, Content, Notification, Subscription, User
from app.utils import role_required

content_bp = Blueprint("content", __name__)

DEFAULT_AVATAR = "https://ui-avatars.com/api/?background=random&name="
DEFAULT_COVER = (
    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=600&auto=format&fit=crop"
)
BASE_URL = "http://127.0.0.1:5001"

# Banned terms array (Add Moringa policy terms / inappropriate words here)
FORBIDDEN_WORDS = [
    "abuse", "cheat", "plagiarize", "exploit", "spam", "hate",
    # Add school-specific policy terms here
]

def check_policy_violations(title, description):
    """Returns True if the title or description violates guidelines."""
    text_to_check = f"{title} {description}".lower()
    return any(word.lower() in text_to_check for word in FORBIDDEN_WORDS)


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    if isinstance(identity, dict):
        val = identity.get("id") or identity.get("UserID") or identity.get("user_id")
        return int(val) if val is not None else None
    return int(identity)


def _notify_subscribers(content_item):
    """Send notifications to users subscribed to this content's categories."""
    notifications = []
    for category in content_item.categories:
        subscriptions = Subscription.query.filter_by(
            CategoryID=category.CategoryID
        ).all()
        for sub in subscriptions:
            if sub.UserID != content_item.UserID:
                notifications.append(
                    Notification(
                        UserID=sub.UserID,
                        ContentID=content_item.ContentID,
                        Message=f"New content in your feed: '{content_item.Title}'",
                    )
                )

    if notifications:
        db.session.add_all(notifications)
        db.session.commit()


# -------------------------------------------------------------------
# 1. LIST CONTENT (WITH PAGINATION)
# -------------------------------------------------------------------
@content_bp.get("")
@jwt_required(optional=True)
def list_content():
    """List content items with optional filtering and pagination.
    ---
    tags:
      - Content
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 10
      - name: category_id
        in: query
        type: integer
      - name: category
        in: query
        type: string
        description: Category ID or name string
      - name: status
        in: query
        type: string
        default: Published
        enum: [Published, Draft, Archived, Pending, all]
      - name: type
        in: query
        type: string
        enum: [Article, Video, Audio, Image]
    responses:
      200:
        description: Paginated list of content items returned successfully.
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    category_id = request.args.get("category_id", type=int)
    category_name = request.args.get("category")
    status = request.args.get("status", "Published")
    content_type = request.args.get("type")

    query = Content.query

    # 1. Filter Category
    if category_id:
        query = query.filter(
            Content.categories.any(Category.CategoryID == category_id)
        )
    elif category_name and category_name.lower() != "all":
        if category_name.isdigit():
            query = query.filter(
                Content.categories.any(Category.CategoryID == int(category_name))
            )
        else:
            query = query.filter(
                Content.categories.any(
                    Category.Name.ilike(f"%{category_name.strip()}%")
                )
            )

    # 2. Filter Content Type
    if content_type:
        query = query.filter(Content.ContentType.ilike(f"%{content_type}%"))

    # 3. Filter Status
    if status and status.lower() != "all":
        query = query.filter_by(Status=status)

    # 4. Apply Pagination
    paginated_query = query.order_by(Content.CreatedAt.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items_data = []
    for content in paginated_query.items:
        author_username = (
            content.author.Username
            if getattr(content, "author", None)
            else "Anonymous"
        )
        profile_img = None
        if getattr(content, "author", None) and getattr(
            content.author, "profile", None
        ):
            profile_img = getattr(content.author.profile, "ProfileImage", None)

        if not profile_img:
            profile_img = f"{DEFAULT_AVATAR}{author_username}"
        elif not profile_img.startswith("http"):
            profile_img = f"{BASE_URL}{profile_img}"

        content_img = content.ContentURL
        if not content_img:
            content_img = DEFAULT_COVER
        elif not content_img.startswith("http"):
            content_img = f"{BASE_URL}{content_img}"

        items_data.append({
            "id": content.ContentID,
            "content_id": content.ContentID,
            "title": content.Title,
            "description": content.Description,
            "content_type": content.ContentType,
            "content_image": content_img,
            "content_url": content.ContentURL or content_img,
            "status": content.Status,
            "is_approved": getattr(content, "IsApproved", False),
            "author_id": content.UserID,
            "author": {
                "username": author_username,
                "profile_image": profile_img,
            },
            "views_count": getattr(content, "ViewsCount", 0),
            "likes_count": getattr(content, "LikesCount", 0),
            "categories": [
                {"id": cat.CategoryID, "name": cat.Name}
                for cat in content.categories
            ],
            "created_at": (
                content.CreatedAt.isoformat() if content.CreatedAt else None
            ),
        })

    return (
        jsonify({
            "items": items_data,
            "pagination": {
                "total_items": paginated_query.total,
                "total_pages": paginated_query.pages,
                "current_page": paginated_query.page,
                "per_page": paginated_query.per_page,
                "has_next": paginated_query.has_next,
                "has_prev": paginated_query.has_prev,
            },
        }),
        200,
    )


# -------------------------------------------------------------------
# 2. GET SINGLE CONTENT
# -------------------------------------------------------------------
@content_bp.get("/<int:content_id>")
def get_single_content(content_id):
    """Get single content details by Content ID."""
    item = db.session.get(Content, content_id)
    if not item:
        return jsonify({"error": "Content not found"}), 404

    author_data = {
        "username": "Anonymous",
        "profile_image": f"{DEFAULT_AVATAR}Anonymous",
    }
    if getattr(item, "author", None):
        author_data["username"] = item.author.Username
        profile_img = (
            getattr(item.author.profile, "ProfileImage", None)
            if getattr(item.author, "profile", None)
            else None
        )
        if not profile_img:
            author_data["profile_image"] = f"{DEFAULT_AVATAR}{item.author.Username}"
        else:
            author_data["profile_image"] = (
                profile_img
                if profile_img.startswith("http")
                else f"{BASE_URL}{profile_img}"
            )

    content_img = item.ContentURL if item.ContentURL else DEFAULT_COVER
    if content_img and not content_img.startswith("http"):
        content_img = f"{BASE_URL}{content_img}"

    return (
        jsonify({
            "id": item.ContentID,
            "content_id": item.ContentID,
            "title": item.Title,
            "description": item.Description,
            "type": item.ContentType,
            "content_type": item.ContentType,
            "content_image": content_img,
            "url": item.ContentURL,
            "content_url": item.ContentURL,
            "status": item.Status,
            "is_approved": getattr(item, "IsApproved", False),
            "author_id": item.UserID,
            "author": author_data,
            "categories": [
                {"id": cat.CategoryID, "name": cat.Name}
                for cat in item.categories
            ],
            "created_at": (
                item.CreatedAt.isoformat() if item.CreatedAt else None
            ),
        }),
        200,
    )


# -------------------------------------------------------------------
# 3. CREATE CONTENT
# -------------------------------------------------------------------
@content_bp.post("")
@jwt_required()
def create_content():
    """Create a new content post."""
    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Unauthorized user"}), 401

        current_user = db.session.get(User, user_id)
        if not current_user:
            return jsonify({"error": "User not found"}), 404

        if request.is_json:
            data = request.get_json() or {}
            file = None
        else:
            data = request.form.to_dict()
            file = request.files.get("file") or request.files.get("content_url")

        title = data.get("title") or data.get("Title")
        description = (
            data.get("description")
            or data.get("Description")
            or data.get("body")
            or ""
        )
        content_type = (
            data.get("content_type") or data.get("type") or "Article"
        )
        category_id = data.get("category_id") or data.get("categoryId")

        if not title:
            return jsonify({"error": "Title is required"}), 400

        file_url = data.get("content_url") or ""
        if file:
            filename = secure_filename(file.filename)
            upload_dir = current_app.config.get(
                "UPLOAD_FOLDER",
                os.path.join(current_app.root_path, "..", "static", "uploads"),
            )
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            file.save(save_path)
            file_url = f"/static/uploads/{filename}"

        # Enforce workflow based on user role
        normalized_role = str(current_user.Role).lower().replace(" ", "_") if current_user.Role else ""
        if normalized_role in ["admin", "tech_writer"]:
            req_status = str(data.get("status", "")).capitalize()
            status = req_status if req_status in ["Draft", "Published", "Archived"] else "Published"
            is_approved = True if status == "Published" else False
        else:
            # Regular user submissions must be approved by Admin or Tech Writer
            status = "Pending"
            is_approved = False

        new_content = Content(
            Title=title,
            Description=description,
            ContentType=content_type,
            ContentURL=file_url,
            Status=status,
            UserID=user_id,
        )
        if hasattr(new_content, "IsApproved"):
            new_content.IsApproved = is_approved

        if category_id:
            try:
                category = db.session.get(Category, int(category_id))
                if category:
                    new_content.categories.append(category)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid Category ID format"}), 400

        db.session.add(new_content)
        db.session.commit()

        if status == "Published":
            try:
                _notify_subscribers(new_content)
            except Exception:
                db.session.rollback()

        return (
            jsonify({
                "message": (
                    "Content submitted successfully and published!"
                    if status == "Published"
                    else "Content submitted successfully and is pending approval."
                ),
                "content_id": new_content.ContentID,
                "status": new_content.Status,
                "is_approved": is_approved,
            }),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to submit content", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 4. EDIT CONTENT (PUT/PATCH)
# -------------------------------------------------------------------
def _handle_edit_content(content_id):
    """Core update logic shared by PUT and PATCH handlers."""
    item = db.session.get(Content, content_id)
    if not item:
        return jsonify({"error": "Content not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    normalized_role = str(current_user.Role).lower().replace(" ", "_") if current_user.Role else ""
    if item.UserID != current_user.UserID and normalized_role != "admin":
        return (
            jsonify({"error": "Forbidden: Cannot edit another user's content"}),
            403,
        )

    if request.is_json:
        data = request.get_json() or {}
        file = None
    else:
        data = request.form.to_dict()
        file = request.files.get("file") or request.files.get("content_url")

    raw_type = data.get("type") or data.get("content_type")
    if raw_type:
        formatted_type = str(raw_type).capitalize()
        allowed_types = ["Article", "Video", "Audio", "Image"]
        if formatted_type not in allowed_types:
            return (
                jsonify({
                    "error": (
                        "Invalid Content type. Must be one of: "
                        + ", ".join(allowed_types)
                    )
                }),
                400,
            )
        item.ContentType = formatted_type

    if file:
        filename = secure_filename(file.filename)
        upload_dir = current_app.config.get(
            "UPLOAD_FOLDER",
            os.path.join(current_app.root_path, "..", "static", "uploads"),
        )
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)
        item.ContentURL = f"/static/uploads/{filename}"
    elif "url" in data or "content_url" in data:
        item.ContentURL = data.get("url") or data.get("content_url")

    if "status" in data:
        req_status = str(data.get("status")).capitalize()
        if req_status in ["Draft", "Published", "Archived", "Pending"]:
            item.Status = req_status

    if "title" in data or "Title" in data:
        item.Title = data.get("title") or data.get("Title")
    if "description" in data or "Description" in data or "body" in data:
        item.Description = (
            data.get("description") or data.get("Description") or data.get("body")
        )

    category_id = (
        data.get("category_id") or data.get("category") or data.get("categoryId")
    )
    if category_id:
        try:
            category = db.session.get(Category, int(category_id))
            if not category:
                return jsonify({"error": "Category not found"}), 404
            item.categories = [category]
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid Category ID format"}), 400

    try:
        db.session.commit()
        return (
            jsonify({
                "message": "Content updated successfully.",
                "content": {
                    "id": item.ContentID,
                    "title": item.Title,
                    "content_type": item.ContentType,
                    "status": item.Status,
                    "content_url": item.ContentURL,
                },
            }),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to update content", "details": str(e)}),
            500,
        )


@content_bp.put("/<int:content_id>")
@jwt_required()
def update_content_put(content_id):
    return _handle_edit_content(content_id)


@content_bp.patch("/<int:content_id>")
@jwt_required()
def update_content_patch(content_id):
    return _handle_edit_content(content_id)


# -------------------------------------------------------------------
# 5. DELETE CONTENT
# -------------------------------------------------------------------
@content_bp.delete("/<int:content_id>")
@jwt_required()
def delete_content(content_id):
    item = db.session.get(Content, content_id)
    if not item:
        return jsonify({"error": "Content not found"}), 404

    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    current_user = db.session.get(User, user_id)
    if not current_user:
        return jsonify({"error": "User not found"}), 404

    normalized_role = str(current_user.Role).lower().replace(" ", "_") if current_user.Role else ""
    if item.UserID != current_user.UserID and normalized_role != "admin":
        return jsonify({"error": "Forbidden: Cannot delete this item"}), 403

    try:
        db.session.delete(item)
        db.session.commit()
        return (
            jsonify({
                "message": "Content deleted successfully.",
                "content_id": content_id,
            }),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to delete content", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 6. APPROVE CONTENT (ADMIN & TECH WRITER)
# -------------------------------------------------------------------
@content_bp.patch("/<int:content_id>/approve")
@jwt_required()
@role_required("Admin", "Tech Writer", "tech_writer")
def approve_content(content_id):
    """Approve content post and change status to Published."""
    item = db.session.get(Content, content_id)
    if not item:
        return jsonify({"error": "Content not found"}), 404

    try:
        item.Status = "Published"
        if hasattr(item, "IsApproved"):
            item.IsApproved = True
        if hasattr(item, "RejectionReason"):
            item.RejectionReason = None

        if getattr(item, "UserID", None):
            notif = Notification(
                UserID=item.UserID,
                ContentID=item.ContentID,
                Message=f"Your submission '{item.Title}' has been approved and published!",
            )
            db.session.add(notif)

        db.session.commit()
        _notify_subscribers(item)

        return (
            jsonify({
                "message": "Content approved and published successfully.",
                "content_id": content_id,
                "status": item.Status,
                "is_approved": True,
            }),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to approve content", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 7. FLAG CONTENT (ADMIN & TECH WRITER)
# -------------------------------------------------------------------
@content_bp.patch("/<int:content_id>/flag")
@jwt_required()
@role_required("Admin", "Tech Writer", "tech_writer")
def flag_content(content_id):
    """Flag content and move status to Archived/Rejected."""
    item = db.session.get(Content, content_id)
    if not item:
        return jsonify({"error": "Content not found"}), 404

    data = request.get_json(silent=True) or {}
    reason = data.get("reason", "Violated platform rules and guidelines.")

    try:
        if hasattr(item, "IsApproved"):
            item.IsApproved = False
        if hasattr(item, "RejectionReason"):
            item.RejectionReason = reason

        item.Status = "Archived"

        if getattr(item, "UserID", None):
            notif = Notification(
                UserID=item.UserID,
                ContentID=item.ContentID,
                Message=f"Your content '{item.Title}' was flagged/archived. Reason: {reason}",
            )
            db.session.add(notif)

        db.session.commit()

        return (
            jsonify({
                "message": "Content flagged and archived successfully.",
                "content_id": content_id,
                "status": item.Status,
                "is_approved": getattr(item, "IsApproved", False),
            }),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to flag content", "details": str(e)}),
            500,
        )