import click

from .extensions import db


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables (temporary, until the initial migration exists)."""
        db.create_all()
        click.echo("Tables created.")
