from sqlalchemy import Column, Integer, String, DateTime, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models import Base

# Junction table untuk many-to-many relationship Role <-> Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow),
    Column("updated_at", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(191), nullable=False, unique=True)
    description = Column(String(191), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Many-to-many relationship dengan Role
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, slug='{self.slug}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_by_slug(cls, db_session, slug: str):
        """Helper method untuk get permission by slug"""
        return db_session.query(cls).filter(cls.slug == slug).first()

    @classmethod
    def get_by_slugs(cls, db_session, slugs: list):
        """Helper method untuk get multiple permissions by slugs"""
        return db_session.query(cls).filter(cls.slug.in_(slugs)).all()

    @classmethod
    def get_all_paginated(cls, db_session, skip: int = 0, limit: int = 100):
        """Helper method untuk get paginated permissions"""
        return db_session.query(cls).offset(skip).limit(limit).all()

    @classmethod
    def count_all(cls, db_session):
        """Helper method untuk count total permissions"""
        return db_session.query(cls).count()

    @classmethod
    def search_by_slug_or_description(
        cls, db_session, search_term: str, skip: int = 0, limit: int = 100
    ):
        """Helper method untuk search permissions by slug or description"""
        search_pattern = f"%{search_term}%"
        return (
            db_session.query(cls)
            .filter(
                (cls.slug.like(search_pattern)) | (cls.description.like(search_pattern))
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
