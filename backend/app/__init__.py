import os
from datetime import timedelta
from flask import Flask, jsonify
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.extensions import bcrypt, cors, db, jwt, limiter, ma, migrate
from config import config_by_name


# Enable Foreign Key Support in SQLite databases
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


def create_app(config_class=None, config_name=None):
    if config_class is None:
        config_class = config_name or "development"
    app = Flask(__name__)

    app.config.from_object(config_by_name[config_class])
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": "*"
            }
        }
    )
    ma.init_app(app)
    limiter.init_app(app)

    with app.app_context():
        from app import models

    from app.routes.admin import admin_bp
    from app.routes.ai_routes import ai_bp
    from app.routes.auth_profile import auth_profile_bp
    from app.routes.categories import categories_bp
    from app.routes.comment_reactions import comment_reactions_bp
    from app.routes.comments import comments_bp
    from app.routes.content import content_bp
    from app.routes.interactions import interactions_bp
    from app.routes.media import media_bp  # Registered media upload blueprint
    from app.routes.notifications import notifications_bp
    from app.routes.profile import profiles_bp
    from app.routes.reports import reports_bp
    from app.routes.subscriptions import subscriptions_bp

    app.register_blueprint(auth_profile_bp, url_prefix="/api")
    app.register_blueprint(profiles_bp, url_prefix="/api/profiles")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(content_bp, url_prefix="/api/content")
    app.register_blueprint(media_bp)  # Handles /api/upload
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    app.register_blueprint(comments_bp, url_prefix="/api")
    app.register_blueprint(interactions_bp, url_prefix="/api")
    app.register_blueprint(
        notifications_bp,
        url_prefix="/api/notifications"
    )
    app.register_blueprint(
        subscriptions_bp,
        url_prefix="/api/subscriptions"
    )
    app.register_blueprint(
        comment_reactions_bp,
        url_prefix="/api"
    )
    app.register_blueprint(
        reports_bp,
        url_prefix="/api"
    )
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    from werkzeug.exceptions import HTTPException
    from app.schema_doctor import (
        check_and_repair,
        looks_like_schema_drift,
        schema_drift_hint,
    )

    _drift_repair_attempted = False

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            "error": "File size exceeds the maximum permitted limit of 50MB."
        }), 413

    @app.errorhandler(Exception)
    def handle_uncaught_error(error):
        nonlocal _drift_repair_attempted

        if isinstance(error, HTTPException):
            return jsonify({"error": error.description}), error.code

        app.logger.exception("Unhandled exception")

        details = str(error)
        message = "Internal server error"
        if looks_like_schema_drift(details):
            if not _drift_repair_attempted:
                _drift_repair_attempted = True
                try:
                    repaired = check_and_repair(app, verbose=False)
                    app.logger.warning(
                        "Schema drift detected mid-request — auto-repair ran: %s",
                        "schema updated" if repaired else "nothing to update",
                    )
                    if repaired:
                        return (
                            jsonify({
                                "error": "Database schema was just repaired automatically. Please retry.",
                                "schema_repaired": True,
                                "retry": True,
                            }),
                            503,
                        )
                except Exception:
                    app.logger.exception("Mid-request schema auto-repair failed")
            message = schema_drift_hint()

        return jsonify({"error": message, "details": details}), 500

    if os.environ.get("MORINGA_AUTO_REPAIR") == "1" and not app.config.get("TESTING"):
        try:
            from app.schema_doctor import check_and_repair

            if check_and_repair(app, verbose=False):
                print("ℹ schema was out of date — repaired automatically "
                      "(run `python setup_db.py` for full output)")
        except Exception:
            app.logger.exception("Startup schema self-check failed")

    @app.get("/")
    def index():
        return jsonify({
            "message": "My Moringa Daily app"
        })

    return app