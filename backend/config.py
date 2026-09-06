import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)


class Config:

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "dev-secret-key-change-in-production"
    )

    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY",
        "jwt-secret-change-me"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # Uploads directory served by Flask static
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads")

    # 50 MB upload ceiling (matches app/__init__.py and route error handlers)
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024

    # Password reset
    FRONTEND_URL = os.environ.get(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    PASSWORD_RESET_TOKEN_MAX_AGE = int(
        os.environ.get(
            "PASSWORD_RESET_TOKEN_MAX_AGE",
            "3600"
        )
    )

    # SMTP email configuration
    MAIL_SERVER = os.environ.get(
        "MAIL_SERVER",
        "smtp.gmail.com"
    )

    MAIL_PORT = int(
        os.environ.get(
            "MAIL_PORT",
            "587"
        )
    )

    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")

    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")

    MAIL_USE_TLS = os.environ.get(
        "MAIL_USE_TLS",
        "true"
    ).lower() == "true"


class DevelopmentConfig(Config):
    DEBUG = True

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    )


def _normalize_database_uri(uri):
    """Normalize postgres:// URLs to postgresql:// for SQLAlchemy 1.4+ compatibility."""
    if uri and uri.startswith("postgres://"):
        return uri.replace("postgres://", "postgresql://", 1)
    return uri


class ProductionConfig(Config):
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = _normalize_database_uri(
        os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
        )
    )


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}