import os

# Enable automatic database schema repair when starting the backend.
# This fixes databases created from older versions of the models.
os.environ.setdefault("MORINGA_AUTO_REPAIR", "1")

from app import create_app

# FLASK_ENV=production on Render/Heroku-style hosts; defaults to development
config_name = os.environ.get("FLASK_ENV", "development")

app = create_app(config_name=config_name)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=(config_name != "production"),
        port=5001
    )
