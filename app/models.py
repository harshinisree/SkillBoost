from sqlalchemy import func

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("student", "staff", "admin", name="user_role"), nullable=False
    )
    status = db.Column(
        db.Enum("pending", "approved", name="user_status"),
        nullable=False,
        default="pending",
    )
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    def to_dict(self):
        """Safe public view of a user. Never includes the password hash."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Course(db.Model):
    __tablename__ = "courses"
    __table_args__ = (
        db.CheckConstraint("capacity >= 1", name="ck_courses_capacity_positive"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    capacity = db.Column(db.Integer, nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "capacity": self.capacity,
            "staff_id": self.staff_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Enrollment(db.Model):
    __tablename__ = "enrollments"
    __table_args__ = (
        db.UniqueConstraint("student_id", "course_id", name="uq_enrollments_student_course"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False, index=True)
    enrolled_at = db.Column(db.DateTime, nullable=False, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "enrolled_at": self.enrolled_at.isoformat() if self.enrolled_at else None,
        }
