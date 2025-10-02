from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.document import Document, DocumentHistory, DocumentRevision
from app.models.user import User
from app.schemas.document import (
    DocumentHistoryResponse,
    DocumentHistoryCreate,
    DocumentHistoryUpdate,
    HistoryAction,
)
from app.config.database import get_db
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[DocumentHistoryResponse])
async def get_all_history(
    skip: int = 0,
    limit: int = 100,
    document_id: Optional[int] = None,
    action: Optional[HistoryAction] = None,
    performed_by: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DocumentHistory)

    if document_id is not None:
        query = query.filter(DocumentHistory.document_id == document_id)
    if action is not None:
        query = query.filter(DocumentHistory.action == action)
    if performed_by is not None:
        query = query.filter(DocumentHistory.performed_by == performed_by)

    history = (
        query.order_by(DocumentHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return history


@router.post(
    "/", response_model=DocumentHistoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_history(
    history_data: DocumentHistoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = (
        db.query(Document).filter(Document.id == history_data.document_id).first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if history_data.revision_id:
        revision = (
            db.query(DocumentRevision)
            .filter(
                DocumentRevision.id == history_data.revision_id,
                DocumentRevision.document_id == history_data.document_id,
            )
            .first()
        )
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revision not found or doesn't belong to this document",
            )

    history_dict = history_data.dict()
    history_dict["performed_by"] = current_user.id

    new_history = DocumentHistory(**history_dict)
    db.add(new_history)
    db.commit()
    db.refresh(new_history)

    return new_history


@router.get("/{history_id}", response_model=DocumentHistoryResponse)
async def get_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = db.query(DocumentHistory).filter(DocumentHistory.id == history_id).first()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document history not found"
        )

    return history


@router.put("/{history_id}", response_model=DocumentHistoryResponse)
async def update_history(
    history_id: int,
    history_data: DocumentHistoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = db.query(DocumentHistory).filter(DocumentHistory.id == history_id).first()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document history not found"
        )

    if history_data.revision_id is not None:
        revision = (
            db.query(DocumentRevision)
            .filter(
                DocumentRevision.id == history_data.revision_id,
                DocumentRevision.document_id == history.document_id,
            )
            .first()
        )
        if not revision:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Revision not found or doesn't belong to this document",
            )

    update_data = history_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(history, field, value)

    db.commit()
    db.refresh(history)

    return history


@router.delete("/{history_id}")
async def delete_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    history = db.query(DocumentHistory).filter(DocumentHistory.id == history_id).first()

    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document history not found"
        )

    db.delete(history)
    db.commit()

    return {
        "message": "Document history deleted successfully",
        "deleted_history_id": history_id,
    }


@router.get("/document/{document_id}", response_model=List[DocumentHistoryResponse])
async def get_history_by_document(
    document_id: int,
    skip: int = 0,
    limit: int = 100,
    action: Optional[HistoryAction] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    query = db.query(DocumentHistory).filter(DocumentHistory.document_id == document_id)

    if action is not None:
        query = query.filter(DocumentHistory.action == action)

    history = (
        query.order_by(DocumentHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return history


@router.post("/log", response_model=DocumentHistoryResponse)
async def log_action(
    document_id: int,
    action: HistoryAction,
    revision_id: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    new_history = DocumentHistory(
        document_id=document_id,
        action=action,
        revision_id=revision_id,
        reason=reason,
        performed_by=current_user.id,
    )

    db.add(new_history)
    db.commit()
    db.refresh(new_history)

    return new_history


@router.get("/analytics/summary")
async def get_history_summary(
    document_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import func

    query = db.query(
        DocumentHistory.action, func.count(DocumentHistory.id).label("count")
    )

    if document_id:
        query = query.filter(DocumentHistory.document_id == document_id)

    if start_date:
        from datetime import datetime

        start_dt = datetime.fromisoformat(start_date)
        query = query.filter(DocumentHistory.created_at >= start_dt)

    if end_date:
        from datetime import datetime

        end_dt = datetime.fromisoformat(end_date)
        query = query.filter(DocumentHistory.created_at <= end_dt)

    results = query.group_by(DocumentHistory.action).all()

    summary = {
        "total_actions": sum(r.count for r in results),
        "actions_breakdown": {r.action.value: r.count for r in results},
    }

    return summary
