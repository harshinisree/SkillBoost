"""The OpenAPI 3.1 description of the API, served at /openapi.json (T4-6).

Request bodies and query parameters are generated from the same Pydantic
schemas the routes validate with, so they cannot drift. A test checks that
every route in the app appears here, and nothing else.
"""
from .schemas import (
    CourseListQuery,
    CourseSchema,
    EnrollSchema,
    LoginSchema,
    RegisterSchema,
)

REQUEST_SCHEMAS = {
    "RegisterBody": RegisterSchema,
    "LoginBody": LoginSchema,
    "CourseBody": CourseSchema,
    "EnrollBody": EnrollSchema,
}

_TIME = {"type": ["string", "null"], "format": "date-time"}
RESPONSE_SCHEMAS = {
    "Error": {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {"code": {"type": "string"}, "message": {"type": "string"}},
            }
        },
    },
    "Health": {"type": "object", "properties": {"status": {"type": "string", "example": "ok"}}},
    "User": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "role": {"type": "string", "enum": ["student", "staff", "admin"]},
            "status": {"type": "string", "enum": ["pending", "approved"]},
            "created_at": _TIME,
        },
    },
    "UserList": {"type": "object", "properties": {"items": {"type": "array", "items": {"$ref": "#/components/schemas/User"}}}},
    "Token": {
        "type": "object",
        "properties": {
            "access_token": {"type": "string"},
            "token_type": {"type": "string", "example": "Bearer"},
            "expires_in": {"type": "integer", "example": 3600},
        },
    },
    "Course": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "capacity": {"type": "integer"},
            "staff_id": {"type": "integer"},
            "created_at": _TIME,
        },
    },
    "CourseList": {
        "type": "object",
        "properties": {
            "items": {"type": "array", "items": {"$ref": "#/components/schemas/Course"}},
            "page": {"type": "integer"},
            "per_page": {"type": "integer"},
            "total": {"type": "integer"},
        },
    },
    "Enrollment": {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "student_id": {"type": "integer"},
            "course_id": {"type": "integer"},
            "enrolled_at": _TIME,
        },
    },
    "MyEnrollments": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "course_id": {"type": "integer"},
                        "title": {"type": "string"},
                        "enrolled_at": _TIME,
                    },
                },
            }
        },
    },
}

ERROR_TEXT = {
    400: "Invalid input (VALIDATION_ERROR)",
    401: "Missing, invalid, or expired token (UNAUTHORIZED)",
    403: "Logged in, but not allowed (FORBIDDEN)",
    404: "Not found (NOT_FOUND)",
    409: "Conflict",
    429: "Too many login attempts (TOO_MANY_REQUESTS)",
}

# method, path, tag, summary, role (None = public), request body, success code,
# success schema, error codes, and specific 409 meaning where it applies.
OPERATIONS = [
    ("get", "/health", "System", "Health check", None, None, 200, "Health", [], None),
    ("post", "/auth/register", "Auth", "Register; the account starts pending", None, "RegisterBody", 201, "User", [400, 409], "EMAIL_TAKEN"),
    ("post", "/auth/login", "Auth", "Log in and get a 1-hour token", None, "LoginBody", 200, "Token", [400, 401, 403, 429], None),
    ("get", "/admin/pending", "Admin", "List accounts waiting for approval", "admin", None, 200, "UserList", [401, 403], None),
    ("post", "/admin/approve/{user_id}", "Admin", "Approve an account (recorded in the audit log)", "admin", None, 200, "User", [401, 403, 404], None),
    ("get", "/courses", "Courses", "Browse courses with search, sort, and pages", "any approved user", None, 200, "CourseList", [400, 401], None),
    ("post", "/courses", "Courses", "Create a course", "staff", "CourseBody", 201, "Course", [400, 401, 403], None),
    ("put", "/courses/{course_id}", "Courses", "Replace a course (owner only)", "staff", "CourseBody", 200, "Course", [400, 401, 403, 404], None),
    ("delete", "/courses/{course_id}", "Courses", "Delete a course (owner only, no students enrolled)", "staff", None, 204, None, [401, 403, 404, 409], "COURSE_HAS_ENROLLMENTS"),
    ("post", "/enrollments", "Enrollments", "Enroll in a course (never past its seat limit)", "student", "EnrollBody", 201, "Enrollment", [400, 401, 403, 404, 409], "ALREADY_ENROLLED or COURSE_FULL"),
    ("delete", "/enrollments/{course_id}", "Enrollments", "Drop a course", "student", None, 204, None, [401, 403, 404], None),
    ("get", "/enrollments/me", "Enrollments", "My enrollments with course titles", "student", None, 200, "MyEnrollments", [401, 403], None),
]


def _ref(name):
    return {"$ref": f"#/components/schemas/{name}"}


def _course_list_parameters():
    schema = CourseListQuery.model_json_schema()
    return [
        {"name": name, "in": "query", "required": False, "schema": prop}
        for name, prop in schema["properties"].items()
    ]


def _operation(method, path, tag, summary, role, body, status, success, errors, conflict):
    operation = {"tags": [tag], "summary": summary, "responses": {}}
    if role is not None:
        operation["security"] = [{"bearerAuth": []}]
        operation["description"] = f"Requires a token. Allowed: {role}."
    parameters = [
        {"name": part[1:-1], "in": "path", "required": True, "schema": {"type": "integer"}}
        for part in path.split("/")
        if part.startswith("{")
    ]
    if method == "get" and path == "/courses":
        parameters += _course_list_parameters()
    if parameters:
        operation["parameters"] = parameters
    if body is not None:
        operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": _ref(body)}}}

    ok = {"description": "Success"}
    if success is not None:
        ok["content"] = {"application/json": {"schema": _ref(success)}}
    operation["responses"][str(status)] = ok
    for code in errors:
        text = ERROR_TEXT[code] if code != 409 else f"Conflict ({conflict})"
        operation["responses"][str(code)] = {
            "description": text,
            "content": {"application/json": {"schema": _ref("Error")}},
        }
    return operation


def build_spec():
    components = dict(RESPONSE_SCHEMAS)
    for name, model in REQUEST_SCHEMAS.items():
        components[name] = model.model_json_schema()
    paths = {}
    for method, path, *rest in OPERATIONS:
        paths.setdefault(path, {})[method] = _operation(method, path, *rest)
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "SkillBoost API",
            "version": "1.0.0",
            "description": "Online learning backend: approval-gated accounts, staff-owned courses, "
            "and seat-limited enrollment that holds under concurrency. Every error has the shape "
            '{"error": {"code": ..., "message": ...}}.',
        },
        "paths": paths,
        "components": {
            "schemas": components,
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
        },
    }
