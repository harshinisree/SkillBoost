"""Demo data for trying the API by hand (T4-6). Safe to run more than once.

Creates an admin, two staff, five approved students, one pending student,
ten courses, and enrollments, including one course that is already full.
Every demo account uses DEMO_PASSWORD. For local use only.
"""
from .errors import AppError
from .extensions import db
from .models import Course, User
from .services import course_service, enrollment_service, user_service

DEMO_PASSWORD = "DemoPass123!"
DOMAIN = "skillboost-demo.com"

ADMIN = ("Demo Admin", f"admin@{DOMAIN}")
STAFF = [("Meena Iyer", f"meena@{DOMAIN}"), ("Arjun Rao", f"arjun@{DOMAIN}")]
STUDENTS = [
    ("Ravi Kumar", f"ravi@{DOMAIN}"),
    ("Priya Nair", f"priya@{DOMAIN}"),
    ("Karthik S", f"karthik@{DOMAIN}"),
    ("Divya Menon", f"divya@{DOMAIN}"),
    ("Sanjay Patel", f"sanjay@{DOMAIN}"),
]
PENDING_STUDENT = ("Anu Thomas", f"anu@{DOMAIN}")

# (title, description, capacity, index into STAFF)
COURSES = [
    ("Python for Backend Beginners", "From variables to a working Flask API in 6 weeks.", 30, 0),
    ("SQL Fundamentals", "Queries, joins, and indexes with MySQL.", 25, 0),
    ("Git and GitHub Essentials", "Branches, pull requests, and CI.", 40, 1),
    ("REST API Design", "Resources, status codes, and error formats.", 20, 1),
    ("Flask in Practice", "Blueprints, services, and testing.", 20, 0),
    ("Testing with pytest", "Fixtures, mocking, and coverage.", 15, 1),
    ("Docker for Developers", "Images, containers, and Compose.", 20, 1),
    ("Data Structures in Python", "Lists, dicts, sets, heaps, and their costs.", 30, 0),
    ("System Design Basics", "Caching, queues, and scaling. Two seats only: it fills up.", 2, 1),
    ("Web Security Fundamentals", "Passwords, tokens, and the OWASP Top 10.", 25, 0),
]

# (student index, course index) pairs. Course 8 has 2 seats and both are taken.
ENROLLMENTS = [
    (0, 0), (0, 1), (0, 8),
    (1, 0), (1, 3), (1, 8),
    (2, 2), (2, 5),
    (3, 4), (3, 6), (3, 9),
    (4, 7),
]


def _user(name, email, role, approve_by=None):
    """Return the user with this email, creating (and approving) it if missing."""
    user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
    if user is not None:
        return user, False
    if role == "admin":
        return user_service.create_admin(name, email, DEMO_PASSWORD), True
    user = user_service.register(name, email, DEMO_PASSWORD, role)
    if approve_by is not None:
        user_service.approve(user.id, approve_by)  # also writes an audit row
    return user, True


def run_seed():
    """Create whatever demo data is missing. Returns counts of what was added."""
    added = {"users": 0, "courses": 0, "enrollments": 0}

    admin, new = _user(*ADMIN, "admin")
    added["users"] += new
    staff = []
    for name, email in STAFF:
        user, new = _user(name, email, "staff", approve_by=admin)
        staff.append(user)
        added["users"] += new
    students = []
    for name, email in STUDENTS:
        user, new = _user(name, email, "student", approve_by=admin)
        students.append(user)
        added["users"] += new
    _, new = _user(*PENDING_STUDENT, "student")  # left pending, to try the approval flow
    added["users"] += new

    courses = []
    for title, description, capacity, owner in COURSES:
        course = db.session.execute(
            db.select(Course).filter_by(title=title, staff_id=staff[owner].id)
        ).scalar_one_or_none()
        if course is None:
            course = course_service.create(staff[owner], title, description, capacity)
            added["courses"] += 1
        courses.append(course)

    for student_index, course_index in ENROLLMENTS:
        try:
            enrollment_service.enroll(students[student_index], courses[course_index].id)
            added["enrollments"] += 1
        except AppError:
            pass  # already enrolled from an earlier run

    return added


def demo_logins():
    """(role, email) rows for the README and the command's output."""
    rows = [("admin", ADMIN[1])]
    rows += [("staff", email) for _, email in STAFF]
    rows += [("student", email) for _, email in STUDENTS]
    rows.append(("student, pending approval", PENDING_STUDENT[1]))
    return rows
