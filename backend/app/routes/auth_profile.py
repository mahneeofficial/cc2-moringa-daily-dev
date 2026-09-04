import os
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.utils import secure_filename

from app.email_service import send_password_reset_email
from app.extensions import db,bcrypt
from app.models import Content, Profile, User

auth_profile_bp = Blueprint("auth_profile", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


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
def register():
    """Register a new user
    ---
    tags:
      - Authentication
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              example: johndoe
            email:
              type: string
              example: johndoe@example.com
            password:
              type: string
              example: yourpassword123
            role:
              type: string
              example: user
    responses:
      201:
        description: User registered successfully
      400:
        description: Missing required fields or invalid data
      409:
        description: Username or email already exists
      500:
        description: Database commit error
    """
    # Parse payload gracefully from JSON or Form submission
    data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
    
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required."}), 400

    allowed_roles = ["user", "tech_writer", "Admin"]
    if role not in allowed_roles:
        role = "user"

    existing_user = User.query.filter(
        (User.Username == username) | (User.Email == email)
    ).first()

    if existing_user:
        return jsonify({"error": "Username or email already exists"}), 409

    try:
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

        return (
            jsonify({
                "message": "User created successfully.",
                "user": {
                    "id": new_user.UserID,
                    "user_id": new_user.UserID,
                    "username": new_user.Username,
                    "email": new_user.Email,
                    "role": new_user.Role,
                },
            }),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create user account", "details": str(e)}), 500


@auth_profile_bp.post("/login")
def login():
    """Authenticate user and return JWT token
    ---
    tags:
      - Authentication
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: johndoe@example.com
            password:
              type: string
              example: yourpassword123
    responses:
      200:
        description: Authentication successful
      400:
        description: Missing credentials
      401:
        description: Invalid credentials
    """
    data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(Email=email).first()
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

      # Check password logic
    if hasattr(user, "check_password"):
        is_valid_password = user.check_password(password)
    else:
        # Use bcrypt to safely verify against the database column _Password_Hash
        is_valid_password = bcrypt.check_password_hash(user._Password_Hash, password)

    if not is_valid_password:
        return jsonify({"error": "Invalid email or password"}), 401
    # Generate JWT token
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=str(user.UserID))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user.UserID,
            "username": user.Username,
            "email": user.Email,
            "role": user.Role
        }
    }), 200


@auth_profile_bp.post("/reset-password")
def reset_password():
    """Reset password using reset token
    ---
    tags:
      - Authentication
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - token
            - password
          properties:
            token:
              type: string
              example: "eyJhbGciOi..."
            password:
              type: string
              example: newsecurepassword123
    responses:
      200:
        description: Password reset successful
      400:
        description: Invalid token or password format error
      404:
        description: User not found
    """
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


@auth_profile_bp.put("/change-password")
@jwt_required()
def change_password():
    """Change password for currently authenticated user
    ---
    tags:
      - Authentication
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - old_password
            - new_password
          properties:
            old_password:
              type: string
              example: oldpassword123
            new_password:
              type: string
              example: newpassword123
    responses:
      200:
        description: Password updated successfully
      400:
        description: Invalid request or incorrect current password
      401:
        description: Unauthorized / Missing token
      404:
        description: User not found
    """
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


@auth_profile_bp.get("/me")
@jwt_required()
def get_my_profile():
    """Get current authenticated user profile
    ---
    tags:
      - Profile
    security:
      - BearerAuth: []
    responses:
      200:
        description: User profile and post summary retrieved successfully
      401:
        description: Unauthorized / Missing token
      404:
        description: User not found
    """
    current_user_id = safe_get_user_id()

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
    is_admin = getattr(user, "is_admin", False) or (role.lower() == "admin")

    return (
        jsonify({
            "user": {
                "id": user.UserID,
                "user_id": user.UserID,
                "username": user.Username,
                "email": user.Email,
                "role": role,
                "is_admin": is_admin,
            },
            "profile": {
                "profile_id": profile.ProfileID,
                "bio": profile.Bio or "",
                "skills": profile.Skills or "",
                "interests": profile.Interests or "",
                "profile_image": profile.ProfileImage or "",
                "posts_count": len(user_posts),
                "posts": posts_data,
            },
        }),
        200,
    )


@auth_profile_bp.patch("/me")
@jwt_required()
def update_profile():
    """Update profile details (Bio, Interests, Skills, GitHub, Profile Image)
    ---
    tags:
      - Profile
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            bio:
              type: string
              example: Full-stack developer passionate about open source.
            interests:
              type: string
              example: Web Development, Machine Learning
            skills:
              type: string
              example: Python, Flask, React, PostgreSQL
            github_profile:
              type: string
              example: https://github.com/octocat
            profile_image:
              type: string
              example: /static/uploads/avatars/avatar_user_1.png
    responses:
      200:
        description: Profile updated successfully
      401:
        description: Missing or invalid Authorization header
    """
    current_user_id = safe_get_user_id()

    profile = Profile.query.filter_by(UserID=current_user_id).first()
    if not profile:
        profile = Profile(UserID=current_user_id)
        db.session.add(profile)

    data = request.get_json(silent=True) or {}

    profile.Bio = data.get("bio", profile.Bio)
    profile.Interests = data.get("interests", profile.Interests)
    profile.Skills = data.get("skills", profile.Skills)

    if "skills" in data or "tech_stack" in data:
        profile.Skills = data.get("skills") or data.get("tech_stack")

    if "github_profile" in data or "github" in data or "githubUrl" in data:
        profile.GithubProfile = (
            data.get("github_profile") or data.get("github") or data.get("githubUrl")
        )

    if "profile_image" in data or "profileImage" in data:
        profile.ProfileImage = data.get("profile_image") or data.get("profileImage")

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully.",
        "profile": {
            "profile_id": profile.ProfileID,
            "user_id": profile.UserID,
            "bio": profile.Bio or "",
            "interests": profile.Interests or "",
            "skills": getattr(profile, "Skills", "") or "",
            "github_profile": getattr(profile, "GithubProfile", "") or "",
            "profile_image": profile.ProfileImage or "",
        }
    }), 200


@auth_profile_bp.patch("/avatar")
@jwt_required()
def update_profile_avatar():
    """Upload profile picture
    ---
    tags:
      - Profile
    security:
      - BearerAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - name: profile_picture
        in: formData
        type: file
        description: Profile image file (png, jpg, jpeg, webp, gif)
    responses:
      200:
        description: Profile picture updated successfully
      400:
        description: No file provided or invalid file format
      401:
        description: Unauthorized
    """
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


@auth_profile_bp.get("/users/<int:user_id>")
def get_public_profile(user_id):
    """Get public profile of a user by User ID
    ---
    tags:
      - Profile
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID of the requested user
    responses:
      200:
        description: Public profile details retrieved
      404:
        description: User not found
    """
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