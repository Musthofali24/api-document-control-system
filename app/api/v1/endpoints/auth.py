from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.config.database import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshTokenResponse,
)
from app.core.auth import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user,
)
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint - autentikasi user dengan email dan password
    """
    # Cari user berdasarkan email (case insensitive)
    user = db.query(User).filter(User.email.ilike(login_data.email)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Verify password
    if not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Buat access token
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(ACCESS_TOKEN_EXPIRE_MINUTES) * 60,  # dalam detik
        user=user.to_dict(),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(current_user: User = Depends(get_current_user)):
    return LogoutResponse(message="Successfully logged out", success=True)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token using current valid token
    """
    # Buat access token baru
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": str(current_user.id), "email": current_user.email},
        expires_delta=access_token_expires,
    )

    return RefreshTokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(ACCESS_TOKEN_EXPIRE_MINUTES) * 60,  # dalam detik
    )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }
