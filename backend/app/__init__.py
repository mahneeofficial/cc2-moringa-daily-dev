import os
from datetime import timedelta
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

from config import DevelopmentConfig, config_by_name
from app.extensions import db, jwt, migrate, bcrypt, ma,swagger

def create_app(config_name=None):
    app = Flask(__name__, static_folder="../static")
    app.url_map.strict_slashes = False

    # Load configuration
    if not config_name:
        config_name = os.getenv("FLASK_ENV", "development")

    config_class = config_by_name.get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    # Fallback default database URI
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
            app.root_path, "app.db"
        )
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=5)


    # Swagger Documentation Config with JWT Security Spec
    app.config["SWAGGER"] = {
        "title": "Moringa Daily API Documentation",
        "uiversion": 3,
        "openapi": "3.0.2",
        "specs_route": "/apidocs/",
        "components": {
            "securitySchemes": {
                "Bearer": {
                    "type": "apiKey",
                    "name": "Authorization",
                    "in": "header",
                    "description": 'JWT Authorization header using the Bearer scheme. Example: "Authorization: Bearer {token}"'
                }
            }
        }
    }

    # Global CORS setup (handles preflight OPTIONS automatically)
    CORS(
        app,
        resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    ma.init_app(app)
    swagger.init_app(app)

    # Serve uploaded static media files
    @app.route("/static/uploads/<path:filename>")
    def serve_upload(filename):
        upload_dir = os.path.join(app.root_path, "..", "static", "uploads")
        return send_from_directory(upload_dir, filename)

    # Import models within application context
    with app.app_context():
        from app import models

    # Import route Blueprints from app/routes/
    from app.routes.admin import admin_bp
    from app.routes.auth_profile import auth_profile_bp
    from app.routes.categories import categories_bp
    from app.routes.comment_reactions import comment_reactions_bp
    from app.routes.comments import comments_bp
    from app.routes.content import content_bp
    from app.routes.interactions import interactions_bp
    from app.routes.notifications import notifications_bp
    from app.routes.reports import reports_bp
    from app.routes.subscriptions import subscriptions_bp

    # Register Blueprints
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(auth_profile_bp, url_prefix="/api/auth")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(content_bp, url_prefix="/api/content")
    app.register_blueprint(comments_bp, url_prefix="/api")
    app.register_blueprint(interactions_bp, url_prefix="/api")
    app.register_blueprint(
        notifications_bp,
        url_prefix="/api/users/me/notifications"
    )
    app.register_blueprint(subscriptions_bp, url_prefix="/api/user/me/subscriptions")
    app.register_blueprint(comment_reactions_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")

    # Root route
    @app.get("/")
    def index():
        return jsonify({"status": "online", "message": "API Server Operational"}), 200
    return app