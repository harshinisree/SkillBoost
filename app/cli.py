import click
from pydantic import ValidationError

from .errors import AppError
from .schemas import AccountSchema
from .services import user_service


def register_cli(app):
    @app.cli.command("explain-queries")
    def explain_queries():
        """Print MySQL's EXPLAIN plan for the key queries, as a Markdown table."""
        from .query_report import markdown_report

        click.echo(markdown_report())

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Name", help="Full name of the admin.")
    @click.option("--email", prompt="Email", help="Email address used to log in.")
    @click.password_option(help="Password (asked twice, never shown on screen).")
    def create_admin(name, email, password):
        """Create an approved admin account. Admins cannot be created through the API."""
        try:
            data = AccountSchema.model_validate(
                {"name": name, "email": email, "password": password}
            )
        except ValidationError as err:
            fields = list(dict.fromkeys(str(e["loc"][0]) for e in err.errors() if e["loc"]))
            raise click.ClickException("Invalid " + ", ".join(fields) + ". Nothing was created.")

        try:
            user = user_service.create_admin(data.name, data.email, data.password)
        except AppError as err:
            raise click.ClickException(err.message + " Nothing was created.")

        click.echo(f"Admin {user.email} created.")
