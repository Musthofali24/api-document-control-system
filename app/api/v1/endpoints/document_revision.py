from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.document import Document, DocumentRevision
from app.models.user import User
from app.schemas.document import (
    DocumentRevisionResponse,
    DocumentRevisionCreate,
    DocumentRevisionUpdate,
    RevisionStatus,
)
from app.config.database import get_db
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[DocumentRevisionResponse])
async def get_all_revisions(
    skip: int = 0,
    limit: int = 100,
    document_id: Optional[int] = None,
    status: Optional[RevisionStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/document-revisions/
    Mendapatkan daftar semua document revisions dengan filtering
    """
    query = db.query(DocumentRevision)

    # Filtering
    if document_id is not None:
        query = query.filter(DocumentRevision.document_id == document_id)
    if status is not None:
        query = query.filter(DocumentRevision.status == status)

    revisions = query.offset(skip).limit(limit).all()
    return revisions


@router.post(
    "/", response_model=DocumentRevisionResponse, status_code=status.HTTP_201_CREATED
)
async def create_revision(
    revision_data: DocumentRevisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /api/v1/document-revisions/
    Membuat document revision baru
    """
    # Check apakah document exists
    document = (
        db.query(Document).filter(Document.id == revision_data.document_id).first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check apakah revision_number sudah ada untuk document ini
    existing_revision = (
        db.query(DocumentRevision)
        .filter(
            DocumentRevision.document_id == revision_data.document_id,
            DocumentRevision.revision_number == revision_data.revision_number,
        )
        .first()
    )
    if existing_revision:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Revision number {revision_data.revision_number} already exists for this document",
        )

    # Create revision baru
    revision_dict = revision_data.dict()
    revision_dict["revised_by"] = current_user.id  # Set reviser ke user yang login

    new_revision = DocumentRevision(**revision_dict)
    db.add(new_revision)
    db.commit()
    db.refresh(new_revision)

    return new_revision


@router.get("/{revision_id}", response_model=DocumentRevisionResponse)
async def get_revision(
    revision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/document-revisions/{id}
    Mendapatkan detail document revision berdasarkan ID
    """
    revision = (
        db.query(DocumentRevision).filter(DocumentRevision.id == revision_id).first()
    )

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document revision not found"
        )

    return revision


@router.put("/{revision_id}", response_model=DocumentRevisionResponse)
async def update_revision(
    revision_id: int,
    revision_data: DocumentRevisionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    PUT /api/v1/document-revisions/{id}
    Update data document revision berdasarkan ID
    """
    revision = (
        db.query(DocumentRevision).filter(DocumentRevision.id == revision_id).first()
    )

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document revision not found"
        )

    # Optional: Check permission - hanya reviser yang bisa edit
    # if revision.revised_by != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized to edit this revision")

    # Check revision_number tidak duplicate (jika diupdate)
    if revision_data.revision_number is not None:
        existing_revision = (
            db.query(DocumentRevision)
            .filter(
                DocumentRevision.document_id == revision.document_id,
                DocumentRevision.revision_number == revision_data.revision_number,
                DocumentRevision.id != revision_id,
            )
            .first()
        )
        if existing_revision:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Revision number {revision_data.revision_number} already exists for this document",
            )

    # Update fields yang dikirim
    update_data = revision_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(revision, field, value)

    db.commit()
    db.refresh(revision)

    return revision


@router.delete("/{revision_id}")
async def delete_revision(
    revision_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    DELETE /api/v1/document-revisions/{id}
    Hapus document revision berdasarkan ID
    """
    revision = (
        db.query(DocumentRevision).filter(DocumentRevision.id == revision_id).first()
    )

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document revision not found"
        )

    # Optional: Check permission - hanya reviser atau admin yang bisa delete
    # if revision.revised_by != current_user.id:
    #     raise HTTPException(status_code=403, detail="Not authorized to delete this revision")

    db.delete(revision)
    db.commit()

    return {
        "message": "Document revision deleted successfully",
        "deleted_revision_id": revision_id,
    }


# Nested endpoint: Get revisions for specific document
@router.get("/document/{document_id}", response_model=List[DocumentRevisionResponse])
async def get_revisions_by_document(
    document_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[RevisionStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/document-revisions/document/{document_id}
    Mendapatkan semua revisions dari document tertentu
    """
    # Check document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Get revisions
    query = db.query(DocumentRevision).filter(
        DocumentRevision.document_id == document_id
    )

    if status is not None:
        query = query.filter(DocumentRevision.status == status)

    revisions = (
        query.order_by(DocumentRevision.revision_number.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return revisions


# Status management endpoints
@router.patch("/{revision_id}/status", response_model=DocumentRevisionResponse)
async def update_revision_status(
    revision_id: int,
    new_status: RevisionStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    PATCH /api/v1/document-revisions/{id}/status
    Update status document revision (approve/reject/etc)
    """
    revision = (
        db.query(DocumentRevision).filter(DocumentRevision.id == revision_id).first()
    )

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document revision not found"
        )

    # Business logic untuk status transition
    if (
        revision.status == RevisionStatus.APPROVED
        and new_status != RevisionStatus.APPROVED
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status of already approved revision",
        )

    revision.status = new_status
    db.commit()
    db.refresh(revision)

    return revision


@router.get("/document/{document_id}/latest", response_model=DocumentRevisionResponse)
async def get_latest_revision(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    GET /api/v1/document-revisions/document/{document_id}/latest
    Mendapatkan revision terbaru dari document tertentu
    """
    # Check document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Get latest revision
    latest_revision = (
        db.query(DocumentRevision)
        .filter(DocumentRevision.document_id == document_id)
        .order_by(DocumentRevision.revision_number.desc())
        .first()
    )

    if not latest_revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No revisions found for this document",
        )

    return latest_revision
