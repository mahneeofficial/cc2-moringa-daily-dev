from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from flasgger import Swagger 

# Explicit naming conventions prevent migration failures in Alembic
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

db = SQLAlchemy(metadata=metadata)
jwt = JWTManager()
migrate = Migrate()
cors = CORS()
bcrypt = Bcrypt()
ma = Marshmallow()
<<<<<<< HEAD
swagger= Swagger()
=======
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
>>>>>>> b967a37c7ac44c464ee1430f46bf1c288dbedd03
