from sqlalchemy import Column, Integer, String, DateTime, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.config.database import Base

user_roles = Table(
    "user_role",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.now(timezone.utc)),
    Column(
        "updated_at",
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    ),
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(191), nullable=False, unique=True)
    slug = Column(String(191), nullable=False, unique=True)
    description = Column(String(191), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    users = relationship("User", secondary=user_roles, back_populates="roles")

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
        return db_session.query(cls).filter(cls.name == name).first()

    @classmethod
    def get_by_slug(cls, db_session, slug: str):
        return db_session.query(cls).filter(cls.slug == slug).first()
