from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentResponse, DocumentCreate, DocumentUpdate
from app.config.database import get_db
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=List[DocumentResponse])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Document)

    if category_id is not None:
        query = query.filter(Document.category_id == category_id)
    if is_active is not None:
        query = query.filter(Document.is_active == is_active)

    documents = query.offset(skip).limit(limit).all()
    return documents


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_document = (
        db.query(Document).filter(Document.code == document_data.code).first()
    )
    if existing_document:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document code already exists",
        )

    if document_data.category_id:
        from app.models.category import Category

        category = (
            db.query(Category).filter(Category.id == document_data.category_id).first()
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
            )

    document_dict = document_data.dict()
    document_dict["uploaded_by"] = current_user.id

    new_document = Document(**document_dict)
    db.add(new_document)
    db.commit()
    db.refresh(new_document)

    return new_document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: int,
    document_data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if document_data.code:
        existing_document = (
            db.query(Document)
            .filter(Document.code == document_data.code, Document.id != document_id)
            .first()
        )
        if existing_document:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document code already exists",
            )

    if document_data.category_id:
        from app.models.category import Category

        category = (
            db.query(Category).filter(Category.id == document_data.category_id).first()
        )
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
            )

    update_data = document_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    db.commit()
    db.refresh(document)

    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    db.delete(document)
    db.commit()

    return {
        "message": "Document deleted successfully",
        "deleted_document_id": document_id,
    }


@router.get("/{document_id}/revisions")
async def get_document_revisions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    return {
        "document_id": document_id,
        "revisions": [],
        "message": "Document revisions will be implemented after DocumentRevision endpoints",
    }
