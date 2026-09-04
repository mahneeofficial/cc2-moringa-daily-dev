import os
import time
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from app.email_service import send_password_reset_email
from app.extensions import db
from app.models import Content, Profile, User

auth_profile_bp = Blueprint("auth_profile", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

# ---------------------------------------------------------------------------
# Password-reset email cooldown (in-memory, per email address).
# Once REAL emails are switched on, anyone can hammer /forgot-password and
# burn the SMTP account's daily sending quota (Gmail allows ~500/day) or
# use it to spam victims. One email per address per minute, answered with
# the same generic message so nobody can tell it was throttled.
# ---------------------------------------------------------------------------
RESET_EMAIL_COOLDOWN_SECONDS = 60
_last_reset_request = {}


def _reset_email_on_cooldown(email):
    now = time.time()
    last = _last_reset_request.get(email, 0)
    if now - last < RESET_EMAIL_COOLDOWN_SECONDS:
        return True
    if len(_last_reset_request) > 5000:  # keep the dict tiny forever
        _last_reset_request.clear()
    _last_reset_request[email] = now
    return False


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_get_user_id():
    """Extract integer user ID safely from JWT identity."""
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return int(identity.get("id"))
    return int(identity)


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


# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================


@auth_profile_bp.post("/register")
@auth_profile_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required."}), 400

    # Normalise: "admin"/"Admin"/"ADMIN" all store as "Admin" so role checks
    # and the frontend stay consistent.
    if str(role).lower() == "admin":
        role = "Admin"
    allowed_roles = ["user", "tech_writer", "Admin"]
    if role not in allowed_roles:
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
    if hasattr(new_user, "set_password"):
        new_user.set_password(password)
    else:
        new_user.password_hash = password

    db.session.add(new_user)
    db.session.flush()

    new_profile = Profile(UserID=new_user.UserID)
    db.session.add(new_profile)
    db.session.commit()

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
                "is_admin": str(new_user.Role).lower() == "admin",
            },
        }),
        201,
    )


def _authenticate_and_respond(user, message="Login successful"):
    """Shared login response builder (token + user payload)."""
    access_token = create_access_token(identity=str(user.UserID))
    role = getattr(user, "Role", "user")
    is_admin = getattr(user, "is_admin", False) or (str(role).lower() == "admin")

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
                "is_admin": is_admin,
            },
        }),
        200,
    )


def _find_and_verify_user(identifier, password):
    """Returns (user, error_response). Only one of them is set."""
    if not identifier or not password:
        return None, (jsonify({"error": "Email/username and password are required"}), 400)

    user = User.query.filter(
        (User.Email == identifier) | (User.Username == identifier)
    ).first()

    is_authenticated = False
    if user:
        if hasattr(user, "check_password"):
            is_authenticated = user.check_password(password)
        elif hasattr(user, "authenticate"):
            is_authenticated = user.authenticate(password)

    if not user or not is_authenticated:
        return None, (jsonify({"error": "Invalid email/username or password"}), 401)

    if hasattr(user, "IsActive") and not user.IsActive:
        return None, (jsonify({"error": "Account is inactive"}), 403)

    return user, None


@auth_profile_bp.post("/login")
@auth_profile_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = data.get("email") or data.get("username")
    password = data.get("password")

    user, error = _find_and_verify_user(identifier, password)
    if error:
        return error

    # SECURITY: admin accounts must NOT authenticate through the public
    # login form — they have a dedicated admin login (/admin/login).
    if str(getattr(user, "Role", "user") or "user").lower() == "admin":
        return (
            jsonify({
                "error": (
                    "Admin accounts cannot sign in here. "
                    "Use the admin login page (/admin/login) instead."
                )
            }),
            403,
        )

    return _authenticate_and_respond(user)


@auth_profile_bp.post("/admin/login")
@auth_profile_bp.post("/auth/admin/login")
def admin_login():
    """Dedicated admin sign-in. Only Admin-role accounts are accepted."""
    data = request.get_json(silent=True) or {}
    identifier = data.get("email") or data.get("username")
    password = data.get("password")

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
    email = data.get("email")

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
        # Throttled: answer with the exact same generic message as a normal
        # request — no second email is actually sent.
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
            # Dev convenience: SMTP usually isn't configured locally, so the
            # email can't be sent. Return the reset link directly (dev only)
            # so the forgot -> reset flow is testable without a mail server.
            return jsonify({
                "message": "Email sending is not configured on this server. "
                           "Development mode: use the link below to reset "
                           "your password.",
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
    password = data.get("password")

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

    if hasattr(user, "set_password"):
        user.set_password(password)
    else:
        user.password_hash = password

    db.session.commit()
    return jsonify({"message": "Password reset successful."}), 200


@auth_profile_bp.put("/auth/change-password")
@auth_profile_bp.put("/change-password")
@jwt_required()
def change_password():
    try:
        user_id = safe_get_user_id()
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid user identity"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "Both old and new passwords are required."}), 400

    is_valid_old = False
    if hasattr(user, "check_password"):
        is_valid_old = user.check_password(old_password)
    elif hasattr(user, "authenticate"):
        is_valid_old = user.authenticate(old_password)

    if not is_valid_old:
        return jsonify({"error": "Current password is incorrect."}), 400

    if hasattr(user, "set_password"):
        user.set_password(new_password)
    else:
        user.password_hash = new_password

    db.session.commit()
    return jsonify({"message": "Password updated successfully."}), 200
# ==========================================
# PROFILE ENDPOINTS
# ==========================================

@auth_profile_bp.before_request
def handle_options():
    if request.method == "OPTIONS":
        return "", 200


@auth_profile_bp.get("/me")
@auth_profile_bp.get("/auth/me")
@jwt_required()
def get_my_profile():
    try:
        current_user_id = safe_get_user_id()
    except Exception:
        # Fallback if safe_get_user_id fails
        current_user_id = get_jwt_identity()

    # Handle string identities if JWT stored string ID
    if isinstance(current_user_id, str) and current_user_id.isdigit():
        current_user_id = int(current_user_id)

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

    role = getattr(user, "Role", getattr(user, "role", "user"))
    is_admin = getattr(user, "is_admin", False) or (str(role).lower() == "admin")
    username = getattr(user, "Username", getattr(user, "username", ""))
    email = getattr(user, "Email", getattr(user, "email", ""))

    # Provides all root-level and nested variations React components might look for
    return jsonify({
        "id": user.UserID,
        "user_id": user.UserID,
        "username": username,
        "email": email,
        "role": role,
        "is_admin": is_admin,
        "bio": profile.Bio or "",
        "interests": profile.Interests or "",
        # Skills & GitHub MUST be included here, otherwise every page that
        # reads /me (profile page after reload, navbar, …) shows them empty.
        "skills": getattr(profile, "Skills", "") or "",
        "github_url": getattr(profile, "GithubURL", "") or "",
        "github_profile": getattr(profile, "GithubURL", "") or "",
        "profile_image": profile.ProfileImage or "",
        "posts_count": len(user_posts),
        "posts": posts_data,
        "user": {
            "id": user.UserID,
            "user_id": user.UserID,
            "username": username,
            "email": email,
            "role": role,
            "is_admin": is_admin,
        },
        "profile": {
            "profile_id": profile.ProfileID,
            "bio": profile.Bio or "",
            "interests": profile.Interests or "",
            "skills": getattr(profile, "Skills", "") or "",
            "github_url": getattr(profile, "GithubURL", "") or "",
            "github_profile": getattr(profile, "GithubURL", "") or "",
            "profile_image": profile.ProfileImage or "",
            "posts_count": len(user_posts),
            "posts": posts_data,
        }
    }), 200

# app/routes/auth_profile.py

#===========================================
#UPDATE PROFILE
#===========================================

# NOTE: /api/profiles/me is owned by app/routes/profile.py (profiles_bp).
# These routes only handle /api/me and /api/auth/me so the two blueprints
# never fight over the same URL.
@auth_profile_bp.route("/me", methods=["PUT", "POST", "PATCH", "OPTIONS"])
@auth_profile_bp.route("/auth/me", methods=["PUT", "POST", "PATCH", "OPTIONS"])
def update_profile():
    # 1. Instantly return 200 for CORS preflight OPTIONS requests
    if request.method == "OPTIONS":
        return "", 200

    # 2. Check if the token was sent in the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        print("Backend Error: No Authorization header received.")
        return jsonify({"error": "Missing Authorization header"}), 401

    # 3. Verify the token manually
    from flask_jwt_extended import verify_jwt_in_request
    try:
        verify_jwt_in_request()
    except Exception as e:
        print(f"Backend JWT Error: {str(e)}")
        return jsonify({"error": f"Invalid or expired token: {str(e)}"}), 401

    # 4. Perform the update if token is valid
    current_user_id = safe_get_user_id()

    profile = Profile.query.filter_by(UserID=current_user_id).first()
    if not profile:
        profile = Profile(UserID=current_user_id)
        db.session.add(profile)

    data = request.get_json(silent=True) or {}

    # --- UPDATED FIELD ASSIGNMENTS ---
    profile.Bio = data.get("bio", profile.Bio)
    profile.Interests = data.get("interests", profile.Interests)

    # Add Skills (supports both camelCase and snake_case)
    if "skills" in data or "tech_stack" in data:
        profile.Skills = data.get("skills") or data.get("tech_stack")

    # Add GitHub profile.
    # FIX: the column is called GithubURL — the old code wrote to
    # `GithubProfile`, which doesn't exist, so the URL silently vanished.
    if "github_url" in data or "github_profile" in data or "github" in data or "githubUrl" in data:
        profile.GithubURL = (
            data.get("github_url")
            or data.get("github_profile")
            or data.get("github")
            or data.get("githubUrl")
        )

    # Add Profile Image
    if "profile_image" in data or "profileImage" in data:
        profile.ProfileImage = data.get("profile_image") or data.get("profileImage")

    db.session.commit()

    # --- UPDATED JSON RESPONSE ---
    return jsonify({
        "message": "Profile updated successfully.",
        "profile": {
            "profile_id": profile.ProfileID,
            "user_id": profile.UserID,
            "bio": profile.Bio or "",
            "interests": profile.Interests or "",
            "skills": getattr(profile, "Skills", "") or "",
            "github_url": getattr(profile, "GithubURL", "") or "",
            "github_profile": getattr(profile, "GithubURL", "") or "",
            "profile_image": profile.ProfileImage or "",
        }
    }), 200

# ==========================================
# 1. Blueprint-Level CORS Preflight Handler
# ==========================================
@auth_profile_bp.before_request
def handle_options():
    if request.method == "OPTIONS":
        return "", 200


# ==========================================
# 4. Update Profile Picture
# ==========================================
@auth_profile_bp.route("/auth/avatar", methods=["PATCH", "POST"])
@auth_profile_bp.route("/avatar", methods=["PATCH", "POST"])
@jwt_required()
def update_profile_avatar():
    current_user_id = safe_get_user_id()

    profile = Profile.query.filter_by(UserID=current_user_id).first()
    if not profile:
        profile = Profile(UserID=current_user_id)
        db.session.add(profile)

    file = request.files.get("profile_picture") or request.files.get("avatar")
    if not file or file.filename == "":
        return jsonify({"error": "No avatar file provided"}), 400

    if file and allowed_file(file.filename):
        filename = (
            f"avatar_user_{current_user_id}_{secure_filename(file.filename)}"
        )
        upload_folder = os.path.join(
            current_app.root_path, "static", "uploads", "avatars"
        )
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        profile.ProfileImage = f"/static/uploads/avatars/{filename}"
        db.session.commit()

        return (
            jsonify({
                "message": "Profile picture updated successfully",
                "profile_image": profile.ProfileImage,
            }),
            200,
        )

    return jsonify({"error": "Invalid file format."}), 400


# ==========================================
# 5. Public Profile View
# ==========================================
@auth_profile_bp.get("/users/<int:user_id>")
def get_public_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    profile = Profile.query.filter_by(UserID=user_id).first()

    return (
        jsonify({
            "user_id": user_id,
            "username": user.Username,
            "bio": profile.Bio if profile else "",
            "profile_image": profile.ProfileImage if profile else "",
        }),
        200,
    )