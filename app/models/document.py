from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Enum,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.config.database import Base


class DocumentStatus(enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class RevisionStatus(enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    code = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    category = relationship("Category", back_populates="documents")
    uploader = relationship(
        "User", foreign_keys=[uploaded_by], back_populates="uploaded_documents"
    )
    revisions = relationship(
        "DocumentRevision", back_populates="document", cascade="all, delete-orphan"
    )
    history = relationship(
        "DocumentHistory", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Document(id={self.id}, code='{self.code}', title='{self.title}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "code": self.code,
            "category_id": self.category_id,
            "uploaded_by": self.uploaded_by,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentRevision(Base):
    __tablename__ = "document_revisions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    file_path = Column(Text, nullable=True)
    revised_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    revision_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    acc_format = Column(Integer, nullable=True)
    acc_content = Column(Integer, nullable=True)
    status = Column(Enum(RevisionStatus), default=RevisionStatus.DRAFT, nullable=False)
    revised_doc = Column(String(255), nullable=True)  # Revised document filename/path
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    document = relationship("Document", back_populates="revisions")
    reviser = relationship(
        "User", foreign_keys=[revised_by], back_populates="revised_documents"
    )

    def __repr__(self):
        return f"<DocumentRevision(id={self.id}, document_id={self.document_id}, revision_number={self.revision_number})>"

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "file_path": self.file_path,
            "revised_by": self.revised_by,
            "revision_number": self.revision_number,
            "description": self.description,
            "acc_format": self.acc_format,
            "acc_content": self.acc_content,
            "status": self.status.value if self.status else None,
            "revised_doc": self.revised_doc,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class HistoryAction(enum.Enum):
    CREATED = "created"
    UPDATED = "updated"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    RESTORED = "restored"


class DocumentHistory(Base):
    __tablename__ = "document_history"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    revision_id = Column(Integer, ForeignKey("document_revisions.id"), nullable=True)
    action = Column(Enum(HistoryAction), nullable=False)
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
        nullable=False,
    )

    document = relationship("Document", back_populates="history")
    revision = relationship("DocumentRevision")
    performer = relationship("User")

    def __repr__(self):
        return f"<DocumentHistory(id={self.id}, document_id={self.document_id}, action='{self.action.value}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "revision_id": self.revision_id,
            "action": self.action.value if self.action else None,
            "performed_by": self.performed_by,
            "reason": self.reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
