from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class RevisionStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    REJECTED = "rejected"


class HistoryAction(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    RESTORED = "restored"


class DocumentBase(BaseModel):
    title: str
    code: str
    category_id: Optional[int] = None
    is_active: Optional[bool] = True


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None


class DocumentResponse(DocumentBase):
    id: int
    uploaded_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentRevisionBase(BaseModel):
    file_path: Optional[str] = None
    revision_number: int
    description: Optional[str] = None
    acc_format: Optional[int] = None
    acc_content: Optional[int] = None
    status: RevisionStatus = RevisionStatus.DRAFT
    revised_doc: Optional[str] = None


class DocumentRevisionCreate(DocumentRevisionBase):
    document_id: int


class DocumentRevisionUpdate(BaseModel):
    file_path: Optional[str] = None
    revision_number: Optional[int] = None
    description: Optional[str] = None
    acc_format: Optional[int] = None
    acc_content: Optional[int] = None
    status: Optional[RevisionStatus] = None
    revised_doc: Optional[str] = None


class DocumentRevisionResponse(DocumentRevisionBase):
    id: int
    document_id: int
    revised_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Document History Schemas
class DocumentHistoryBase(BaseModel):
    action: HistoryAction
    revision_id: Optional[int] = None
    reason: Optional[str] = None


class DocumentHistoryCreate(DocumentHistoryBase):
    document_id: int


class DocumentHistoryUpdate(BaseModel):
    action: Optional[HistoryAction] = None
    revision_id: Optional[int] = None
    reason: Optional[str] = None


class DocumentHistoryResponse(DocumentHistoryBase):
    id: int
    document_id: int
    performed_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
