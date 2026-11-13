from flask import Flask

from .cli import register_cli
from .config import Config
from .errors import register_error_handlers
from .extensions import cors, db, limiter
from .logging_setup import configure_logging


def create_app(config_overrides=None):
    """Build and configure the Flask app. Tests pass config_overrides."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    limiter.init_app(app)
    cors.init_app(app, origins=app.config["CORS_ORIGINS"])
    from . import models  # noqa: F401  (makes db.create_all() see the tables)

    configure_logging(app)
    register_error_handlers(app)
    register_cli(app)

    from .routes.admin import bp as admin_bp
    from .routes.auth import bp as auth_bp
    from .routes.courses import bp as courses_bp
    from .routes.enrollments import bp as enrollments_bp
    from .routes.health import bp as health_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(enrollments_bp)
    return app
