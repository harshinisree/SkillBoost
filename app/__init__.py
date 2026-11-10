from flask import Flask

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
    register_error_handlers(app)

    from .routes.health import bp as health_bp

    app.register_blueprint(health_bp)
    return app
