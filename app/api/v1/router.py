from fastapi import APIRouter

from app.api.v1.endpoints import users, auth, category, document

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

api_router.include_router(users.router, prefix="/users", tags=["Users"])

api_router.include_router(category.router, prefix="/categories", tags=["Categories"])

api_router.include_router(document.router, prefix="/documents", tags=["Documents"])
