"""T4-11: one migration builds the whole schema, matches the models, and reverses cleanly.

These tests rebuild the test database through the migration, then put it back
the way the rest of the suite expects.
"""
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from flask_migrate import downgrade, upgrade
from sqlalchemy import inspect, text

from app.extensions import db

TABLES = {"users", "courses", "enrollments", "audit_log"}


def _drop_everything():
    db.drop_all()
    db.session.execute(text("DROP TABLE IF EXISTS alembic_version"))
    db.session.commit()


def _table_names():
    return set(inspect(db.engine).get_table_names())


@pytest.fixture()
def empty_database(app):
    """An empty test database for one test; the normal tables are restored afterwards."""
    with app.app_context():
        _drop_everything()
        yield
        db.session.remove()
        _drop_everything()
        db.create_all()


def test_t4_11_upgrade_builds_every_table_from_an_empty_database(app, empty_database):
    assert _table_names() == set()

    upgrade()

    assert _table_names() == TABLES | {"alembic_version"}


def test_t4_11_migration_matches_the_models_exactly(app, empty_database):
    upgrade()

    with db.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, db.metadata)

    assert differences == []


def test_t4_11_migration_keeps_the_database_safety_nets(app, empty_database):
    upgrade()

    inspector = inspect(db.engine)
    assert any(c["name"] == "ck_courses_capacity_positive" for c in inspector.get_check_constraints("courses"))
    assert any(
        u["column_names"] == ["student_id", "course_id"] for u in inspector.get_unique_constraints("enrollments")
    )
    assert {fk["referred_table"] for fk in inspector.get_foreign_keys("enrollments")} == {"users", "courses"}


def test_t4_11_downgrade_removes_every_table(app, empty_database):
    upgrade()

    downgrade(revision="base")

    assert _table_names() == {"alembic_version"}
