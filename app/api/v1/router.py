from fastapi import APIRouter

from app.api.v1.endpoints import (
    users,
    auth,
    category,
    document,
    document_revision,
    document_history,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

api_router.include_router(users.router, prefix="/users", tags=["Users"])

api_router.include_router(category.router, prefix="/categories", tags=["Categories"])

api_router.include_router(document.router, prefix="/documents", tags=["Documents"])

api_router.include_router(
    document_revision.router, prefix="/document-revisions", tags=["Document Revision"]
)

api_router.include_router(
    document_history.router, prefix="/document-history", tags=["Document History"]
)
