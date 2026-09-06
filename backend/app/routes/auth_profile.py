import os
import time

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from app.email_service import send_password_reset_email
from app.extensions import db
from app.models import Content, Profile, User
from app.routes.notifications import notify_login, notify_signup

auth_profile_bp = Blueprint("auth_profile", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

RESET_EMAIL_COOLDOWN_SECONDS = 60
_last_reset_request = {}


def _reset_email_on_cooldown(email):
    now = time.time()
    last = _last_reset_request.get(email, 0)
    if now - last < RESET_EMAIL_COOLDOWN_SECONDS:
        return True
    if len(_last_reset_request) > 5000:
        _last_reset_request.clear()
    _last_reset_request[email] = now
    return False


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity."""
    identity = get_jwt_identity()
    if not identity:
        return None
    try:
        if isinstance(identity, dict):
            return int(
                identity.get("id")
                or identity.get("user_id")
                or identity.get("UserID")
            )
        return int(identity)
    except (ValueError, TypeError):
        return None


def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="password-reset")


def verify_reset_token(token):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    max_age = current_app.config.get("PASSWORD_RESET_TOKEN_MAX_AGE", 3600)
    try:
        return serializer.loads(token, salt="password-reset", max_age=max_age)
    except (SignatureExpired, BadSignature):
        return None


@auth_profile_bp.before_request
def handle_options():
    if request.method == "OPTIONS":
        return "", 200


# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@auth_profile_bp.post("/register")
@auth_profile_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username") or data.get("Username")
    email = data.get("email") or data.get("Email")
    password = data.get("password") or data.get("Password")
    role = data.get("role") or data.get("Role") or "user"

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required."}), 400

    allowed_roles = ["user", "tech_writer"]
    if str(role).lower() not in allowed_roles:
        role = "user"

    existing_user = User.query.filter(
        (User.Username == username) | (User.Email == email)
    ).first()

    if existing_user:
        return jsonify({"error": "Username or email already exists"}), 409

    new_user = User(
        Username=username,
        Email=email,
        Role=role,
        IsActive=True,
    )
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.flush()

    new_profile = Profile(UserID=new_user.UserID)
    db.session.add(new_profile)
    db.session.commit()

    notify_signup(new_user.UserID, new_user.Username)

    access_token = create_access_token(identity=str(new_user.UserID))

    return (
        jsonify({
            "message": "User created successfully.",
            "token": access_token,
            "access_token": access_token,
            "user": {
                "id": new_user.UserID,
                "user_id": new_user.UserID,
                "username": new_user.Username,
                "email": new_user.Email,
                "role": new_user.Role,
                "is_active": new_user.IsActive,
                "is_admin": False,
            },
        }),
        201,
    )


def _authenticate_and_respond(user, message="Login successful"):
    access_token = create_access_token(identity=str(user.UserID))
    role = getattr(user, "Role", "user")
    is_admin = str(role).lower() == "admin"

    notify_login(user.UserID, user.Username)

    return (
        jsonify({
            "token": access_token,
            "access_token": access_token,
            "message": message,
            "user": {
                "id": user.UserID,
                "user_id": user.UserID,
                "username": user.Username,
                "email": user.Email,
                "role": role,
                "is_active": getattr(user, "IsActive", True),
                "is_admin": is_admin,
            },
        }),
        200,
    )


def _find_and_verify_user(identifier, password):
    if not identifier or not password:
        return None, (jsonify({"error": "Email/username and password are required"}), 400)

    user = User.query.filter(
        (User.Email == identifier) | (User.Username == identifier)
    ).first()

    is_authenticated = False
    if user:
        is_authenticated = user.check_password(password)

    if not user or not is_authenticated:
        return None, (jsonify({"error": "Invalid email/username or password"}), 401)

    if hasattr(user, "IsActive") and not user.IsActive:
        return None, (jsonify({"error": "Account is inactive"}), 403)

    return user, None


@auth_profile_bp.post("/login")
@auth_profile_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = data.get("email") or data.get("username") or data.get("Email") or data.get("Username")
    password = data.get("password") or data.get("Password")

    user, error = _find_and_verify_user(identifier, password)
    if error:
        return error

    return _authenticate_and_respond(user)


@auth_profile_bp.post("/admin/login")
@auth_profile_bp.post("/auth/admin/login")
def admin_login():
    data = request.get_json(silent=True) or {}
    identifier = data.get("email") or data.get("username") or data.get("Email") or data.get("Username")
    password = data.get("password") or data.get("Password")

    user, error = _find_and_verify_user(identifier, password)
    if error:
        return error

    if str(getattr(user, "Role", "user") or "user").lower() != "admin":
        return (
            jsonify({"error": "This account is not an admin account."}),
            403,
        )

    return _authenticate_and_respond(user, message="Admin login successful")


@auth_profile_bp.post("/auth/logout")
@auth_profile_bp.post("/logout")
def logout():
    return jsonify({"message": "Logout successful."}), 200


@auth_profile_bp.post("/auth/forgot-password")
@auth_profile_bp.post("/forgot-password")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = data.get("email") or data.get("Email")

    if not email:
        return jsonify({"error": "Email is required."}), 400

    user = User.query.filter_by(Email=email).first()
    if not user:
        return (
            jsonify({
                "message": "If an account with that email exists, instructions have been sent."
            }),
            200,
        )

    if _reset_email_on_cooldown(user.Email):
        return (
            jsonify({
                "message": "If an account with that email exists, instructions have been sent."
            }),
            200,
        )

    token = generate_reset_token(user.Email)
    frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_url}/reset-password?token={token}"

    try:
        send_password_reset_email(user.Email, reset_url)
    except Exception:
        current_app.logger.exception("Failed to send password reset email.")
        if current_app.config.get("DEBUG"):
            return jsonify({
                "message": "Email sending is not configured on this server. Development mode link below.",
                "dev_reset_url": reset_url,
            }), 200
        return jsonify({"error": "Unable to send password reset email."}), 500

    return (
        jsonify({
            "message": "If an account with that email exists, instructions have been sent."
        }),
        200,
    )


@auth_profile_bp.post("/auth/reset-password")
@auth_profile_bp.post("/reset-password")
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get("token")
    password = data.get("password") or data.get("Password")

    if not token or not password:
        return jsonify({"error": "Token and password are required."}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    email = verify_reset_token(token)
    if not email:
        return jsonify({"error": "Invalid or expired reset token."}), 400

    user = User.query.filter_by(Email=email).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    user.set_password(password)

    db.session.commit()
    return jsonify({"message": "Password reset successful."}), 200


@auth_profile_bp.put("/auth/change-password")
@auth_profile_bp.put("/change-password")
@jwt_required()
def change_password():
    user_id = safe_get_user_id()
    if not user_id:
        return jsonify({"error": "Invalid user identity"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password") or data.get("oldPassword")
    new_password = data.get("new_password") or data.get("newPassword")

    if not old_password or not new_password:
        return jsonify({"error": "Both old and new passwords are required."}), 400

    if not user.check_password(old_password):
        return jsonify({"error": "Current password is incorrect."}), 400

    user.set_password(new_password)

    db.session.commit()
    return jsonify({"message": "Password updated successfully."}), 200


# ==========================================
# PROFILE ENDPOINTS
# ==========================================

@auth_profile_bp.get("/me")
@auth_profile_bp.get("/auth/me")
@jwt_required()
def get_my_profile():
    current_user_id = safe_get_user_id()
    if not current_user_id:
        return jsonify({"error": "Invalid token or user identity"}), 401

    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = Profile.query.filter_by(UserID=current_user_id).first()
    if not profile:
        profile = Profile(
            UserID=current_user_id, Bio="", Interests="", ProfileImage=""
        )
        db.session.add(profile)
        db.session.commit()

    user_posts = Content.query.filter_by(UserID=current_user_id).all()
    posts_data = [
        {
            "id": getattr(p, "ContentID", getattr(p, "id", None)),
            "title": getattr(p, "Title", getattr(p, "title", "Untitled")),
            "created_at": (
                p.CreatedAt.strftime("%d %b %Y")
                if hasattr(p, "CreatedAt") and p.CreatedAt
                else ""
            ),
        }
        for p in user_posts
    ]

    role = getattr(user, "Role", "user")
    is_admin = str(role).lower() == "admin"

    return jsonify({
        "id": user.UserID,
        "user_id": user.UserID,
        "username": user.Username,
        "email": user.Email,
        "role": role,
        "is_active": getattr(user, "IsActive", True),
        "is_admin": is_admin,
        "bio": profile.Bio or "",
        "interests": profile.Interests or "",
        "profile_image": profile.ProfileImage or "",
        "created_at": profile.CreatedAt.isoformat() if hasattr(profile, "CreatedAt") and profile.CreatedAt else None,
        "updated_at": profile.UpdatedAt.isoformat() if hasattr(profile, "UpdatedAt") and profile.UpdatedAt else None,
        "posts_count": len(user_posts),
        "posts": posts_data,
        "user": {
            "id": user.UserID,
            "user_id": user.UserID,
            "username": user.Username,
            "email": user.Email,
            "role": role,
            "is_active": getattr(user, "IsActive", True),
            "is_admin": is_admin,
        },
        "profile": {
            "profile_id": profile.ProfileID,
            "user_id": profile.UserID,
            "bio": profile.Bio or "",
            "interests": profile.Interests or "",
            "profile_image": profile.ProfileImage or "",
            "created_at": profile.CreatedAt.isoformat() if hasattr(profile, "CreatedAt") and profile.CreatedAt else None,
            "updated_at": profile.UpdatedAt.isoformat() if hasattr(profile, "UpdatedAt") and profile.UpdatedAt else None,
            "posts_count": len(user_posts),
            "posts": posts_data,
        }
    }), 200


@auth_profile_bp.route("/me", methods=["PUT", "POST", "PATCH"])
@auth_profile_bp.route("/auth/me", methods=["PUT", "POST", "PATCH"])
@jwt_required()
def update_profile():
    current_user_id = safe_get_user_id()
    if not current_user_id:
        return jsonify({"error": "Invalid token or user identity"}), 401

    profile = Profile.query.filter_by(UserID=current_user_id).first()
    if not profile:
        profile = Profile(UserID=current_user_id)
        db.session.add(profile)

    user = db.session.get(User, current_user_id)

    # Support JSON updates
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if "bio" in data or "Bio" in data:
            profile.Bio = data.get("bio") if "bio" in data else data.get("Bio")
        if "interests" in data or "Interests" in data:
            profile.Interests = data.get("interests") if "interests" in data else data.get("Interests")
        if "profile_image" in data or "ProfileImage" in data:
            profile.ProfileImage = data.get("profile_image") if "profile_image" in data else data.get("ProfileImage")
        if user and ("username" in data or "Username" in data):
            user.Username = data.get("username") if "username" in data else data.get("Username")

    # Support Form Data updates (e.g. multipart/form-data for file uploads)
    else:
        bio = request.form.get("bio") or request.form.get("Bio")
        interests = request.form.get("interests") or request.form.get("Interests")
        username = request.form.get("username") or request.form.get("Username")

        if bio is not None:
            profile.Bio = bio
        if interests is not None:
            profile.Interests = interests
        if user and username:
            user.Username = username

        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, f"user_{current_user_id}_{filename}")
                file.save(file_path)
                profile.ProfileImage = f"/static/uploads/user_{current_user_id}_{filename}"

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully.",
        "bio": profile.Bio or "",
        "interests": profile.Interests or "",
        "profile_image": profile.ProfileImage or "",
        "username": user.Username if user else "",
    }), 200