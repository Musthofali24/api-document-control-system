from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate, UserLogin
from app.config.database import get_db

router = APIRouter()


@router.get("/", response_model=List[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users
