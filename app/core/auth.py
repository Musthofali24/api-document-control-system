import bcrypt
from datetime import datetime, timedelta
import jwt
from jwt.exceptions import PyJWTError
from typing import Optional
import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config.database import get_db

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    try:
        # print(f"Verifying token with SECRET_KEY: {SECRET_KEY}")
        # print(f"Algorithm: {ALGORITHM}")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # print(f"Decoded payload: {payload}")
        user_id_str = payload.get("sub")
        if user_id_str is None:
            # print("No 'sub' in payload")
            return None
        try:
            payload["sub"] = int(user_id_str)
        except (ValueError, TypeError):
            # print(f"Invalid user_id format: {user_id_str}")
            return None
        return payload
    except PyJWTError as e:
        # print(f"JWT Error: {e}")
        return None
    except Exception as e:
        # print(f"Token verification error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        # print(f"Received token: {token[:50]}...")

        payload = verify_token(token)
        # print(f"Token payload: {payload}")
        if payload is None:
            # print("Token verification failed")
            raise credentials_exception

        user_id: int = payload.get("sub")
        if user_id is None:
            # print("No user_id in token")
            raise credentials_exception

        # print(f"Looking for user ID: {user_id}")

    except HTTPException:
        raise
    except Exception as e:
        # print(f"Authentication error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        # print(f"User not found in database: {user_id}")
        raise credentials_exception

    # print(f"User authenticated: {user.email}")
    return user
