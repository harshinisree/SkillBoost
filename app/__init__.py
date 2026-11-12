from flask import Flask

from .cli import register_cli
from .config import Config
from .errors import register_error_handlers
from .extensions import db


def create_app(config_overrides=None):
    """Build and configure the Flask app. Tests pass config_overrides."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    from . import models  # noqa: F401  (makes db.create_all() see the tables)

    register_error_handlers(app)
    register_cli(app)

    from .routes.admin import bp as admin_bp
    from .routes.auth import bp as auth_bp
    from .routes.courses import bp as courses_bp
    from .routes.health import bp as health_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(courses_bp)
    return app
