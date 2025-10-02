from sqlalchemy import Column, Integer, String, DateTime, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models import Base

# Junction table untuk many-to-many relationship User <-> Role
user_roles = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(191), nullable=False, unique=True)
    slug = Column(String(191), nullable=False, unique=True)
    description = Column(String(191), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Many-to-many relationship dengan User
    users = relationship("User", secondary=user_roles, back_populates="roles")

    # Many-to-many relationship dengan Permission
    permissions = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', slug='{self.slug}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_by_name(cls, db_session, name: str):
        """Helper method untuk get role by name"""
        return db_session.query(cls).filter(cls.name == name).first()

    @classmethod
    def get_by_slug(cls, db_session, slug: str):
        """Helper method untuk get role by slug"""
        return db_session.query(cls).filter(cls.slug == slug).first()
