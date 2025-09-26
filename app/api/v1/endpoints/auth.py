from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.config.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, LogoutResponse
from app.core.auth import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login endpoint - autentikasi user dengan email dan password
    """
    # Cari user berdasarkan email
    user = db.query(User).filter(User.email == login_data.email).first()

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
async def logout():
    """
    Logout endpoint - karena JWT stateless, cukup return success message
    Client harus hapus token dari storage
    """
    return LogoutResponse(message="Successfully logged out", success=True)
