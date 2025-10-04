from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, index=True)
    type = Column(String(255), nullable=False)
    notifiable_type = Column(String(255), nullable=False, default="App\\Models\\User")
    notifiable_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    data = Column(Text, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    user = relationship(
        "User", foreign_keys=[notifiable_id], back_populates="notifications"
    )

    def __repr__(self):
        return f"<Notification(id='{self.id}', type='{self.type}', notifiable_id={self.notifiable_id})>"

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "notifiable_type": self.notifiable_type,
            "notifiable_id": self.notifiable_id,
            "data": self.data,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_as_read(self):
        if not self.is_read:
            self.read_at = datetime.utcnow()

    def mark_as_unread(self):
        self.read_at = None

    @classmethod
    def get_by_user(cls, db_session, user_id: int, skip: int = 0, limit: int = 100):
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id)
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_unread_by_user(
        cls, db_session, user_id: int, skip: int = 0, limit: int = 100
    ):
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id, cls.read_at.is_(None))
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_read_by_user(
        cls, db_session, user_id: int, skip: int = 0, limit: int = 100
    ):
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id, cls.read_at.is_not(None))
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def count_by_user(cls, db_session, user_id: int):
        return db_session.query(cls).filter(cls.notifiable_id == user_id).count()

    @classmethod
    def count_unread_by_user(cls, db_session, user_id: int):
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id, cls.read_at.is_(None))
            .count()
        )

    @classmethod
    def get_by_type(
        cls,
        db_session,
        user_id: int,
        notification_type: str,
        skip: int = 0,
        limit: int = 100,
    ):
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id, cls.type == notification_type)
            .order_by(cls.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def mark_all_read_by_user(cls, db_session, user_id: int):
        now = datetime.utcnow()
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id, cls.read_at.is_(None))
            .update({"read_at": now, "updated_at": now})
        )

    @classmethod
    def delete_read_by_user(cls, db_session, user_id: int):
        return (
            db_session.query(cls)
            .filter(cls.notifiable_id == user_id, cls.read_at.is_not(None))
            .delete()
        )
