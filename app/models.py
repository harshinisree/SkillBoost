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
