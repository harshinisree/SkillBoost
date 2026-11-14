from flask import Blueprint, jsonify

from ..openapi import build_spec

bp = Blueprint("docs", __name__)

SWAGGER_UI_VERSION = "5.17.14"  # pinned, so the page never changes unexpectedly

DOCS_PAGE = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>SkillBoost API docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}/swagger-ui-bundle.js"></script>
  <script>window.ui = SwaggerUIBundle({{ url: "/openapi.json", dom_id: "#swagger-ui" }});</script>
</body>
</html>
"""


@bp.get("/openapi.json")
def openapi_json():
    return jsonify(build_spec())


@bp.get("/docs")
def docs_page():
    return DOCS_PAGE, 200, {"Content-Type": "text/html; charset=utf-8"}
