"""T4-9: the README cannot fall behind the code.

The API table must list exactly the routes the app serves, and every relative
link or image in the README must point to a file that exists.
"""
import re
from pathlib import Path

README = Path(__file__).resolve().parents[2] / "README.md"
NOT_API = {"/openapi.json", "/docs"}


def readme_routes():
    """(METHOD, /path/{param}) for each row of the README's API table."""
    routes = set()
    for line in README.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\|\s*(GET|POST|PUT|DELETE)\s*\|\s*`?([^|`]+?)`?\s*\|", line)
        if match:
            method, path = match.groups()
            routes.add((method, re.sub(r"<([^>]+)>", r"{\1}", path.strip())))
    return routes


def app_routes(app):
    routes = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static" or rule.rule in NOT_API or rule.rule.startswith("/_test"):
            continue
        path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            routes.add((method, path))
    return routes


def normalise(routes):
    """The README writes the id parameter as <id>; the code names it user_id or course_id."""
    return {(m, re.sub(r"\{[^}]*id\}", "{id}", p)) for m, p in routes}


def test_t4_9_readme_api_table_lists_exactly_the_apps_routes(app):
    assert normalise(readme_routes()) == normalise(app_routes(app))
    assert len(readme_routes()) == 12


def test_t4_9_readme_relative_links_and_images_exist():
    text = README.read_text(encoding="utf-8")
    targets = re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text)
    local = [t for t in targets if not t.startswith(("http://", "https://", "mailto:"))]

    assert local, "expected the README to link to docs/ and the screenshot"
    for target in local:
        assert (README.parent / target).exists(), f"README links to a missing file: {target}"
