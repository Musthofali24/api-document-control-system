from functools import wraps
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Callable, Any
from app.core.auth import get_current_user
from ..config.database import get_db
from app.models.user import User
from app.models.permission import Permission


def require_permission(permission_slug: str):
    """
    Decorator untuk mengharuskan user memiliki permission tertentu.

    Args:
        permission_slug: Slug permission yang dibutuhkan

    Returns:
        Decorated function yang akan check permission

    Usage:
        @require_permission("users.create")
        @router.post("/users")
        def create_user(...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies dari kwargs
            current_user = None
            db = None

            # Cari current_user dan db dari kwargs
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, "query"):  # Session object
                    db = value

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            if not db:
                raise HTTPException(
                    status_code=500, detail="Database session not available"
                )

            # Check permission
            if not check_user_has_permission(db, current_user.id, permission_slug):
                raise HTTPException(
                    status_code=403, detail=f"Permission '{permission_slug}' required"
                )

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permission_slugs: List[str]):
    """
    Decorator untuk mengharuskan user memiliki minimal satu dari beberapa permission.

    Args:
        permission_slugs: List permission slugs, user hanya perlu punya salah satu

    Returns:
        Decorated function yang akan check permissions

    Usage:
        @require_any_permission(["users.create", "admin.all"])
        @router.post("/users")
        def create_user(...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies dari kwargs
            current_user = None
            db = None

            # Cari current_user dan db dari kwargs
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, "query"):  # Session object
                    db = value

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            if not db:
                raise HTTPException(
                    status_code=500, detail="Database session not available"
                )

            # Check if user has any of the required permissions
            has_permission = False
            for permission_slug in permission_slugs:
                if check_user_has_permission(db, current_user.id, permission_slug):
                    has_permission = True
                    break

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"One of these permissions required: {', '.join(permission_slugs)}",
                )

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(permission_slugs: List[str]):
    """
    Decorator untuk mengharuskan user memiliki semua permission yang disebutkan.

    Args:
        permission_slugs: List permission slugs yang semuanya harus dimiliki user

    Returns:
        Decorated function yang akan check permissions

    Usage:
        @require_all_permissions(["users.create", "users.assign_role"])
        @router.post("/users")
        def create_user_with_role(...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies dari kwargs
            current_user = None
            db = None

            # Cari current_user dan db dari kwargs
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                elif hasattr(value, "query"):  # Session object
                    db = value

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            if not db:
                raise HTTPException(
                    status_code=500, detail="Database session not available"
                )

            # Check if user has all required permissions
            missing_permissions = []
            for permission_slug in permission_slugs:
                if not check_user_has_permission(db, current_user.id, permission_slug):
                    missing_permissions.append(permission_slug)

            if missing_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing required permissions: {', '.join(missing_permissions)}",
                )

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role_name: str):
    """
    Decorator untuk mengharuskan user memiliki role tertentu.

    Args:
        role_name: Nama role yang dibutuhkan

    Returns:
        Decorated function yang akan check role

    Usage:
        @require_role("admin")
        @router.post("/admin/users")
        def create_user_admin(...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies dari kwargs
            current_user = None

            # Cari current_user dari kwargs
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Check role
            user_roles = [role.name for role in current_user.roles]
            if role_name not in user_roles:
                raise HTTPException(
                    status_code=403, detail=f"Role '{role_name}' required"
                )

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_role(role_names: List[str]):
    """
    Decorator untuk mengharuskan user memiliki minimal satu dari beberapa role.

    Args:
        role_names: List role names, user hanya perlu punya salah satu

    Returns:
        Decorated function yang akan check roles

    Usage:
        @require_any_role(["admin", "moderator"])
        @router.post("/moderate")
        def moderate_content(...):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract dependencies dari kwargs
            current_user = None

            # Cari current_user dari kwargs
            for key, value in kwargs.items():
                if isinstance(value, User):
                    current_user = value
                    break

            if not current_user:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Check roles
            user_roles = [role.name for role in current_user.roles]
            has_role = any(role_name in user_roles for role_name in role_names)

            if not has_role:
                raise HTTPException(
                    status_code=403,
                    detail=f"One of these roles required: {', '.join(role_names)}",
                )

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Helper functions
def check_user_has_permission(db: Session, user_id: int, permission_slug: str) -> bool:
    """
    Check apakah user memiliki permission tertentu melalui roles mereka.

    Args:
        db: Database session
        user_id: ID user yang dicek
        permission_slug: Slug permission yang dicek

    Returns:
        True jika user punya permission, False jika tidak
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    permission = Permission.get_by_slug(db, permission_slug)
    if not permission:
        return False

    # Check semua roles user
    for role in user.roles:
        if permission in role.permissions:
            return True

    return False


def get_user_permissions(db: Session, user_id: int) -> List[str]:
    """
    Get semua permission slugs yang dimiliki user melalui roles mereka.

    Args:
        db: Database session
        user_id: ID user

    Returns:
        List permission slugs yang dimiliki user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    permission_slugs = set()
    for role in user.roles:
        for permission in role.permissions:
            permission_slugs.add(permission.slug)

    return list(permission_slugs)


def get_user_roles(db: Session, user_id: int) -> List[str]:
    """
    Get semua role names yang dimiliki user.

    Args:
        db: Database session
        user_id: ID user

    Returns:
        List role names yang dimiliki user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    return [role.name for role in user.roles]


# FastAPI dependency functions
def require_permission_dependency(permission_slug: str):
    """
    FastAPI dependency untuk check permission.

    Usage:
        @router.post("/users")
        def create_user(
            user_data: UserCreate,
            db: Session = Depends(get_db),
            _: None = Depends(require_permission_dependency("users.create"))
        ):
            pass
    """

    def check_permission(
        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ):
        if not check_user_has_permission(db, current_user.id, permission_slug):
            raise HTTPException(
                status_code=403, detail=f"Permission '{permission_slug}' required"
            )
        return None

    return check_permission


def require_role_dependency(role_name: str):
    """
    FastAPI dependency untuk check role.

    Usage:
        @router.post("/admin/users")
        def create_user_admin(
            user_data: UserCreate,
            db: Session = Depends(get_db),
            _: None = Depends(require_role_dependency("admin"))
        ):
            pass
    """

    def check_role(current_user: User = Depends(get_current_user)):
        user_roles = [role.name for role in current_user.roles]
        if role_name not in user_roles:
            raise HTTPException(status_code=403, detail=f"Role '{role_name}' required")
        return None

    return check_role
