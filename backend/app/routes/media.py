import os
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Category, Content, User

# Renamed blueprint to 'media_bp' to prevent collision with content.py's 'content_bp'
media_bp = Blueprint("media", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp3", "wav", "mp4", "webm", "ogg"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB hard cap


def allowed_file(filename):
    """Check if uploaded file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity string or dictionary."""
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


@media_bp.app_errorhandler(413)
def file_too_large(error):
    return (
        jsonify({"error": "File exceeds the maximum allowable upload limit of 50MB."}),
        413,
    )


@media_bp.route("/api/upload", methods=["POST"], strict_slashes=False)
@jwt_required()
def upload_media():
    if "file" not in request.files:
        return jsonify({"error": "No file included in upload request"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return (
            jsonify(
                {
                    "error": "Unsupported file format. Allowed formats: images, audio, video."
                }
            ),
            400,
        )

    upload_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    unique_filename = f"{os.urandom(8).hex()}_{filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    file.save(file_path)

    media_url = f"/static/uploads/{unique_filename}"
    return jsonify({"content_url": media_url}), 201


@media_bp.route("/api/content", methods=["POST"], strict_slashes=False)
@jwt_required()
def create_content():
    user_id = safe_get_user_id()
    if not user_id:
        return jsonify({"error": "Unauthorized user token"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}

    title = data.get("title") or data.get("Title")
    description = data.get("description") or data.get("Description") or ""
    content_type = str(data.get("content_type") or data.get("type") or "Article").capitalize()
    content_url = data.get("content_url") or data.get("url") or ""
    raw_status = data.get("status", "Published")

    if not title:
        return jsonify({"error": "Title is required"}), 400

    # Sanitize inputs against database constraints
    valid_statuses = {"Draft", "Pending", "Published", "Archived"}
    status = raw_status.capitalize() if isinstance(raw_status, str) else "Published"
    if status not in valid_statuses:
        status = "Published"

    valid_types = {"Article", "Video", "Audio", "Image"}
    if content_type not in valid_types:
        content_type = "Article"

    new_content = Content(
        UserID=user_id,
        Title=title,
        Description=description,
        ContentType=content_type,
        ContentURL=content_url,
        Status=status,
    )

    category_id = data.get("category_id") or data.get("category")
    if category_id:
        try:
            category = db.session.get(Category, int(category_id))
            if category:
                new_content.categories.append(category)
        except (ValueError, TypeError):
            pass

    try:
        db.session.add(new_content)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Content submitted successfully!",
                    "content_id": new_content.ContentID,
                    "status": new_content.Status,
                }
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create content", "details": str(e)}), 500