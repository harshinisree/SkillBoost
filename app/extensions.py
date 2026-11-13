from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Counts requests per client IP address. Limits are attached to individual routes.
limiter = Limiter(key_func=get_remote_address)

cors = CORS()
