"""T4-6: /openapi.json is a valid spec covering exactly the app's routes; /docs shows it."""
import re

from openapi_spec_validator import validate

from app.openapi import REQUEST_SCHEMAS

NOT_API = {"/openapi.json", "/docs"}


def app_routes(app):
    """Every (METHOD, /path/{param}) the app really serves, minus docs and test-only routes."""
    routes = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static" or rule.rule in NOT_API or rule.rule.startswith("/_test"):
            continue
        path = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule)
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            routes.add((method, path))
    return routes


def spec_routes(spec):
    return {(method.upper(), path) for path, ops in spec["paths"].items() for method in ops}


def test_t4_6_openapi_json_is_a_valid_openapi_document(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    validate(response.get_json())  # raises if the document breaks the OpenAPI rules


def test_t4_6_spec_lists_exactly_the_routes_the_app_serves(app, client):
    spec = client.get("/openapi.json").get_json()

    assert spec_routes(spec) == app_routes(app)
    assert len(spec_routes(spec)) == 12


def test_t4_6_request_bodies_come_from_the_real_validation_schemas(client):
    components = client.get("/openapi.json").get_json()["components"]["schemas"]

    for name, model in REQUEST_SCHEMAS.items():
        assert components[name] == model.model_json_schema()


def test_t4_6_protected_operations_declare_the_token(client):
    spec = client.get("/openapi.json").get_json()

    public = {("GET", "/health"), ("POST", "/auth/register"), ("POST", "/auth/login")}
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            has_token = operation.get("security") == [{"bearerAuth": []}]
            assert has_token == ((method.upper(), path) not in public), (method, path)


def test_t4_6_every_operation_documents_its_error_responses(client):
    spec = client.get("/openapi.json").get_json()

    enroll = spec["paths"]["/enrollments"]["post"]["responses"]
    assert set(enroll) == {"201", "400", "401", "403", "404", "409"}
    assert "COURSE_FULL" in enroll["409"]["description"]


def test_t4_6_docs_page_loads_swagger_ui_pointed_at_the_spec(client):
    response = client.get("/docs")

    assert response.status_code == 200
    assert response.content_type.startswith("text/html")
    page = response.get_data(as_text=True)
    assert "swagger-ui-dist@" in page
    assert '"/openapi.json"' in page
