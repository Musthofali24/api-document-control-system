from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from passlib.context import CryptContext

from app.models.user import User
from app.schemas.user import UserResponse, UserCreate, UserUpdate, UserLogin
from app.config.database import get_db
from app.core.auth import get_current_user

router = APIRouter()


@router.get("/")
def get_users(
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = db.query(User).offset((page - 1) * per_page).limit(per_page).all()
    return {"users": users, "page": page, "per_page": per_page}


@router.get("/search")
def search_users(
    q: str = "",
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search users by name or email"""
    query = db.query(User)
    if q:
        query = query.filter(User.name.contains(q) | User.email.contains(q))

    users = query.offset((page - 1) * per_page).limit(per_page).all()
    return {"users": users, "search_term": q, "page": page, "per_page": per_page}


@router.get("/profile", response_model=UserResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile"""
    return current_user


@router.get("/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user statistics"""
    total_users = db.query(User).count()
    # For now, assume all users are active (placeholder logic)
    active_users = total_users

    return {
        "total_users": total_users,
        "active_users": active_users,
        "current_user_id": current_user.id,
    }


@router.put("/change-password")
def change_password(
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change current user's password"""
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Verify current password
    if not pwd_context.verify(password_data["current_password"], current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Hash new password
    hashed_password = pwd_context.hash(password_data["new_password"])
    current_user.password = hashed_password

    db.commit()
    return {"message": "Password changed successfully"}


@router.delete("/bulk")
def bulk_delete_users(
    user_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk delete users"""
    user_ids = user_data.get("user_ids", [])

    success_count = 0
    failed_count = 0

    for user_id in user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.id != current_user.id:  # Don't allow deleting self
            db.delete(user)
            success_count += 1
        else:
            failed_count += 1

    db.commit()
    return {"success_count": success_count, "failed_count": failed_count}


@router.put("/profile", response_model=UserResponse)
def update_user_profile(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user's profile"""
    if user_data.name:
        current_user.name = user_data.name
    if user_data.email:
        # Check if email already exists for another user (case insensitive)
        from sqlalchemy import func

        existing_user = (
            db.query(User)
            .filter(
                func.lower(User.email) == func.lower(user_data.email),
                User.id != current_user.id,
            )
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = user_data.email

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Case-insensitive email check
    from sqlalchemy import func

    existing_user = (
        db.query(User)
        .filter(func.lower(User.email) == func.lower(user_data.email))
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(user_data.password)

    db_user = User(name=user_data.name, email=user_data.email, password=hashed_password)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check permission: only admin or self can update
    user_roles = [role.name.lower() for role in current_user.roles]
    is_admin = "admin" in user_roles
    is_self = current_user.id == user_id

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update other users"
        )

    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        # Check for duplicate email (case insensitive)
        from sqlalchemy import func

        existing_user = (
            db.query(User)
            .filter(func.lower(User.email) == func.lower(user_data.email))
            .first()
        )
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = user_data.email

    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Check permission: only admin can delete users
    user_roles = [role.name.lower() for role in current_user.roles]
    is_admin = "admin" in user_roles

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to delete users",
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


# Additional endpoints to match test expectations
