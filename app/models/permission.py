from sqlalchemy import Column, Integer, String, DateTime, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.config.database import Base

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id"), primary_key=True),
    Column("created_at", DateTime, default=datetime.now(timezone.utc)),
    Column(
        "updated_at",
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    ),
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(191), nullable=False, unique=True)
    description = Column(String(191), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

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
        return db_session.query(cls).filter(cls.slug == slug).first()

    @classmethod
    def get_by_slugs(cls, db_session, slugs: list):
        return db_session.query(cls).filter(cls.slug.in_(slugs)).all()

    @classmethod
    def get_all_paginated(cls, db_session, skip: int = 0, limit: int = 100):
        return db_session.query(cls).offset(skip).limit(limit).all()

    @classmethod
    def count_all(cls, db_session):
        return db_session.query(cls).count()

    @classmethod
    def search_by_slug_or_description(
        cls, db_session, search_term: str, skip: int = 0, limit: int = 100
    ):
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
