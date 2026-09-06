import os

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import (
    Category,
    Content,
    ContentReaction,
    Notification,
    Subscription,
    User,
)
from app.routes.notifications import notify_post_submission
from app.utils import iso_utc, role_required

content_bp = Blueprint("content", __name__)


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity."""
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


def _delete_local_file(content_url):
    """Helper to remove static upload file from disk if it exists."""
    if content_url and content_url.startswith("/static/uploads/"):
        filename = os.path.basename(content_url)
        upload_dir = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
        file_path = os.path.join(upload_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                current_app.logger.warning(f"Failed to delete old file {file_path}: {e}")


def _notify_subscribers(content_item):
    """Send notifications to users subscribed to this content's categories."""
    try:
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
    except Exception:
        db.session.rollback()


def _absolute_media_url(url):
    """Turn a relative path into an absolute URL dynamically from the active request context."""
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    
    host = request.host_url.rstrip("/") if request else ""
    return f"{host}{url}" if host else url


def _serialize_content(content, current_user_id=None):
    """Common serializer with N+1 query prevention via preloaded relationships."""
    author_username = (
        content.author.Username
        if getattr(content, "author", None) and getattr(content.author, "Username", None)
        else ""
    )

    profile_img = None
    if getattr(content, "author", None) and getattr(content.author, "profile", None):
        profile_img = getattr(content.author.profile, "ProfileImage", None)

    profile_img = _absolute_media_url(profile_img) if profile_img else None
    file_url = _absolute_media_url(content.ContentURL) if content.ContentURL else ""

    reactions_unloaded = (
        "reactions" in db.inspect(content).unloaded
        if hasattr(content, "__table__")
        else True
    )

    if reactions_unloaded:
        likes_count = ContentReaction.query.filter_by(
            ContentID=content.ContentID, Reaction="like"
        ).count()
        dislikes_count = ContentReaction.query.filter_by(
            ContentID=content.ContentID, Reaction="dislike"
        ).count()
        is_liked = False
        if current_user_id:
            reaction = ContentReaction.query.filter_by(
                ContentID=content.ContentID, UserID=current_user_id
            ).first()
            is_liked = bool(reaction and reaction.Reaction == "like")
    else:
        reactions = getattr(content, "reactions", []) or []
        likes_count = sum(1 for r in reactions if r.Reaction == "like")
        dislikes_count = sum(1 for r in reactions if r.Reaction == "dislike")
        is_liked = bool(
            current_user_id
            and any(
                r.UserID == current_user_id and r.Reaction == "like"
                for r in reactions
            )
        )

    categories = [
        {"id": cat.CategoryID, "name": cat.Name} for cat in content.categories
    ]
    category = categories[0] if categories else None

    comments = getattr(content, "comments", []) or []
    comments_count = len(comments)

    created_at = iso_utc(content.CreatedAt)

    return {
        "id": content.ContentID,
        "content_id": content.ContentID,
        "title": content.Title,
        "description": content.Description,
        "type": content.ContentType,
        "content_type": content.ContentType,
        "url": file_url,
        "content_url": file_url,
        "media_url": file_url,
        "mediaUrl": file_url,
        "content_image": file_url,
        "status": content.Status,
        "is_approved": getattr(content, "IsApproved", False),
        "author_id": content.UserID,
        "author": {
            "username": author_username,
            "profile_image": profile_img,
        },
        "likes_count": likes_count,
        "dislikes_count": dislikes_count,
        "is_liked": is_liked,
        "comments_count": comments_count,
        "categories": categories,
        "category": category,
        "created_at": created_at,
        "createdAt": created_at,
    }


# -------------------------------------------------------------------
# 1. LIST CONTENT (DATABASE PAGINATED)
# -------------------------------------------------------------------
@content_bp.route("", methods=["GET"], strict_slashes=False)
@content_bp.route("/", methods=["GET"], strict_slashes=False)
@jwt_required(optional=True)
def list_content():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)

    category_id = request.args.get("category_id", type=int)
    category_name = request.args.get("category")
    status = request.args.get("status", "Published")
    content_type = request.args.get("type")
    search = (
        request.args.get("search") or request.args.get("q") or ""
    ).strip()

    try:
        current_user_id = safe_get_user_id()
    except Exception:
        current_user_id = None

    query = Content.query.options(
        joinedload(Content.author).joinedload(User.profile),
        selectinload(Content.categories),
        selectinload(Content.comments),
        selectinload(Content.reactions),
    )

    if category_id:
        query = query.filter(
            Content.categories.any(Category.CategoryID == category_id)
        )
    elif category_name and category_name.lower() != "all":
        if category_name.isdigit():
            query = query.filter(
                Content.categories.any(
                    Category.CategoryID == int(category_name)
                )
            )
        else:
            query = query.filter(
                Content.categories.any(
                    Category.Name.ilike(f"%{category_name.strip()}%")
                )
            )

    if content_type:
        query = query.filter(Content.ContentType.ilike(f"%{content_type}%"))

    if status and status.lower() != "all":
        query = query.filter(Content.Status.ilike(status))

    if search:
        like = f"%{search}%"
        query = query.filter(
            db.or_(
                Content.Title.ilike(like),
                Content.Description.ilike(like),
            )
        )

    paginated_query = query.order_by(Content.CreatedAt.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items_data = [
        _serialize_content(content, current_user_id)
        for content in paginated_query.items
    ]

    return (
        jsonify(
            {
                "items": items_data,
                "pagination": {
                    "total_items": paginated_query.total,
                    "total_pages": paginated_query.pages,
                    "current_page": paginated_query.page,
                    "per_page": paginated_query.per_page,
                    "has_next": paginated_query.has_next,
                    "has_prev": paginated_query.has_prev,
                },
            }
        ),
        200,
    )


# -------------------------------------------------------------------
# 2. GET SINGLE CONTENT
# -------------------------------------------------------------------
@content_bp.get("/<int:content_id>")
def get_single_content(content_id):
    item = (
        Content.query.options(
            joinedload(Content.author).joinedload(User.profile),
            selectinload(Content.categories),
            selectinload(Content.comments),
            selectinload(Content.reactions),
        )
        .filter_by(ContentID=content_id)
        .first()
    )

    if not item:
        return jsonify({"error": "Content not found"}), 404

    try:
        current_user_id = safe_get_user_id()
    except Exception:
        current_user_id = None

    return jsonify(_serialize_content(item, current_user_id)), 200


# -------------------------------------------------------------------
# 3. CREATE CONTENT
# -------------------------------------------------------------------
@content_bp.route("", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_content():
    try:
        user_id = safe_get_user_id()
        if not user_id:
            return jsonify({"error": "Unauthorized user"}), 401

        user = db.session.get(User, user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        if request.is_json:
            data = request.get_json(silent=True) or {}
            file = None
        else:
            data = request.form.to_dict()
            file = (
                request.files.get("file")
                or request.files.get("media_file")
                or request.files.get("media")
                or request.files.get("content_url")
            )

        title = data.get("title") or data.get("Title")
        description = (
            data.get("description")
            or data.get("Description")
            or data.get("body")
            or ""
        )

        content_type = (
            data.get("content_type")
            or data.get("type")
            or "Article"
        )
        content_type = str(content_type).capitalize()
        allowed_types = ["Article", "Video", "Audio", "Image"]

        if content_type not in allowed_types:
            return (
                jsonify(
                    {
                        "error": "Invalid Content type. Must be one of: "
                        + ", ".join(allowed_types)
                    }
                ),
                400,
            )

        category_id = (
            data.get("category_id")
            or data.get("categoryId")
            or data.get("category")
        )

        if not title:
            return jsonify({"error": "Title is required"}), 400

        def _save_upload(upload_file):
            filename = secure_filename(upload_file.filename)
            if not filename:
                return None
            upload_dir = current_app.config.get(
                "UPLOAD_FOLDER",
                "static/uploads",
            )
            os.makedirs(upload_dir, exist_ok=True)
            save_path = os.path.join(upload_dir, filename)
            upload_file.save(save_path)
            return f"/static/uploads/{filename}"

        file_url = data.get("content_url") or data.get("url") or ""

        if file:
            saved = _save_upload(file)
            if saved:
                file_url = saved

        user_role = str(
            getattr(user, "Role", getattr(user, "role", "")) or ""
        ).lower()

        if user_role in ("admin", "tech_writer", "techwriter"):
            status = "Published"
            is_approved = True
            published_immediately = True
            publish_reason = "Published automatically based on author role permissions."
        else:
            status = "Pending"
            is_approved = False
            published_immediately = False
            publish_reason = "Posts are reviewed by an admin before they appear in the public feed."

        new_content = Content(
            UserID=user_id,
            Title=title,
            Description=description,
            ContentType=content_type,
            ContentURL=file_url,
            Status=status,
            IsApproved=is_approved,
        )

        if category_id:
            try:
                category = db.session.get(Category, int(category_id))
                if not category:
                    return jsonify({"error": "Category not found"}), 404
                new_content.categories.append(category)
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid Category ID format"}), 400

        db.session.add(new_content)
        db.session.commit()

        if is_approved:
            _notify_subscribers(new_content)
        else:
            try:
                notify_post_submission(
                    user_id, new_content.ContentID, new_content.Title
                )
            except Exception as notify_err:
                current_app.logger.warning(
                    f"Failed to send post submission notification: {notify_err}"
                )

        return (
            jsonify(
                {
                    "message": (
                        "Content published successfully."
                        if is_approved
                        else "Content submitted successfully and sent for review."
                    ),
                    "id": new_content.ContentID,
                    "content_id": new_content.ContentID,
                    "status": new_content.Status,
                    "is_approved": is_approved,
                    "published_immediately": published_immediately,
                    "publish_reason": publish_reason,
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()

        from app.schema_doctor import (
            looks_like_schema_drift,
            schema_drift_hint,
        )

        details = str(e)
        error = "Failed to submit content"
        if looks_like_schema_drift(details):
            error = schema_drift_hint()

        return jsonify({"error": error, "details": details}), 500


# -------------------------------------------------------------------
# 4. EDIT CONTENT (PUT/PATCH)
# -------------------------------------------------------------------
@content_bp.route(
    "/<int:content_id>", methods=["PUT", "PATCH"], strict_slashes=False
)
@jwt_required()
def edit_content(content_id):
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

    user_role = str(
        getattr(current_user, "Role", getattr(current_user, "role", "")) or ""
    ).lower()

    if item.UserID != current_user.UserID and user_role not in ("admin", "tech_writer", "techwriter"):
        return (
            jsonify({"error": "Forbidden: Cannot edit another user's content"}),
            403,
        )

    if request.is_json:
        data = request.get_json() or {}
        file = None
    else:
        data = request.form.to_dict()
        file = (
            request.files.get("file")
            or request.files.get("media_file")
            or request.files.get("media")
            or request.files.get("content_url")
        )

    raw_type = data.get("type") or data.get("content_type")
    if raw_type:
        formatted_type = str(raw_type).capitalize()
        allowed_types = ["Article", "Video", "Audio", "Image"]
        if formatted_type not in allowed_types:
            return (
                jsonify(
                    {
                        "error": f"Invalid Content type. Must be one of: {', '.join(allowed_types)}"
                    }
                ),
                400,
            )
        item.ContentType = formatted_type

    if file:
        filename = secure_filename(file.filename)
        upload_dir = current_app.config.get("UPLOAD_FOLDER", "static/uploads")
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)

        _delete_local_file(item.ContentURL)

        file.save(save_path)
        item.ContentURL = f"/static/uploads/{filename}"
    elif "url" in data or "content_url" in data:
        new_url = data.get("url") or data.get("content_url")
        if new_url != item.ContentURL:
            _delete_local_file(item.ContentURL)
            item.ContentURL = new_url

    if "status" in data:
        req_status = str(data.get("status")).capitalize()
        if req_status in ["Draft", "Pending", "Published", "Archived"]:
            item.Status = req_status

    if "title" in data or "Title" in data:
        item.Title = data.get("title") or data.get("Title")

    if "description" in data or "Description" in data or "body" in data:
        item.Description = (
            data.get("description")
            or data.get("Description")
            or data.get("body")
        )

    category_id = (
        data.get("category_id")
        or data.get("category")
        or data.get("categoryId")
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
            jsonify(
                {
                    "message": "Content updated successfully.",
                    "content": {
                        "id": item.ContentID,
                        "title": item.Title,
                        "content_type": item.ContentType,
                        "status": item.Status,
                        "content_url": item.ContentURL,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to update content", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 5. DELETE CONTENT
# -------------------------------------------------------------------
@content_bp.delete("/<int:content_id>", strict_slashes=False)
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

    user_role = str(
        getattr(current_user, "Role", getattr(current_user, "role", "")) or ""
    ).lower()

    if item.UserID != current_user.UserID and user_role not in ("admin", "tech_writer", "techwriter"):
        return (
            jsonify({"error": "Forbidden: Cannot delete this item"}),
            403,
        )

    try:
        _delete_local_file(item.ContentURL)

        db.session.delete(item)
        db.session.commit()
        return (
            jsonify(
                {
                    "message": "Content deleted successfully.",
                    "content_id": content_id,
                }
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to delete content", "details": str(e)}),
            500,
        )


# -------------------------------------------------------------------
# 6. FLAG CONTENT
# -------------------------------------------------------------------
@content_bp.route(
    "/<int:content_id>/flag", methods=["PATCH"], strict_slashes=False
)
@jwt_required()
@role_required("admin", "Admin", "tech_writer", "Tech_Writer")
def flag_content(content_id):
    item = db.session.get(Content, content_id)
    if not item:
        return jsonify({"error": "Content not found"}), 404

    try:
        if hasattr(item, "IsApproved"):
            item.IsApproved = False

        item.Status = "Archived"
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Content flagged and archived successfully.",
                    "content_id": content_id,
                    "status": item.Status,
                    "is_approved": getattr(item, "IsApproved", False),
                }
            ),
            200,
        )

    except Exception as e:
        db.session.rollback()
        return (
            jsonify({"error": "Failed to flag content", "details": str(e)}),
            500,
        )