from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import math

from app.core.auth import get_current_user
from app.core.permissions import require_role
from ....config.database import get_db
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission, role_permissions
from app.schemas.permission import (
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    PermissionListResponse,
    PermissionSearchResponse,
    RolePermissionAssign,
    RolePermissionUnassign,
    RolePermissionResponse,
    BulkPermissionOperation,
    BulkPermissionResponse,
    UserPermissionCheck,
    UserPermissionResponse,
)

router = APIRouter()


@router.post("/", response_model=PermissionResponse, summary="Create new permission")
@require_role("Admin")
def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if Permission.get_by_slug(db, permission.slug):
        raise HTTPException(
            status_code=400,
            detail=f"Permission with slug '{permission.slug}' already exists",
        )

    db_permission = Permission(
        slug=permission.slug,
        description=permission.description,
    )

    db.add(db_permission)
    db.commit()
    db.refresh(db_permission)

    return db_permission


@router.get("/", response_model=PermissionListResponse, summary="Get all permissions")
def get_permissions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * per_page

    permissions = Permission.get_all_paginated(db, skip=skip, limit=per_page)
    total = Permission.count_all(db)
    total_pages = math.ceil(total / per_page)

    return PermissionListResponse(
        permissions=permissions,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get(
    "/search", response_model=PermissionSearchResponse, summary="Search permissions"
)
def search_permissions(
    q: str = Query(..., min_length=1, description="Search term"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * per_page

    permissions = Permission.search_by_slug_or_description(
        db, q, skip=skip, limit=per_page
    )

    total_permissions = Permission.search_by_slug_or_description(
        db, q, skip=0, limit=1000
    )
    total = len(total_permissions)
    total_pages = math.ceil(total / per_page)

    return PermissionSearchResponse(
        permissions=permissions,
        total=total,
        search_term=q,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
    summary="Get permission by ID",
)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    return permission


@router.put(
    "/{permission_id}", response_model=PermissionResponse, summary="Update permission"
)
@require_role("Admin")
def update_permission(
    permission_id: int,
    permission_update: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    if permission_update.slug and permission_update.slug != permission.slug:
        existing_permission = Permission.get_by_slug(db, permission_update.slug)
        if existing_permission:
            raise HTTPException(
                status_code=400,
                detail=f"Permission with slug '{permission_update.slug}' already exists",
            )

    update_data = permission_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(permission, field, value)

    db.commit()
    db.refresh(permission)

    return permission


@router.delete(
    "/bulk", response_model=BulkPermissionResponse, summary="Bulk delete permissions"
)
@require_role("Admin")
def bulk_delete_permissions(
    bulk_operation: BulkPermissionOperation,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success_count = 0
    failed_count = 0
    failed_permissions = []

    for permission_id in bulk_operation.permission_ids:
        try:
            permission = (
                db.query(Permission).filter(Permission.id == permission_id).first()
            )
            if permission:
                db.delete(permission)
                success_count += 1
            else:
                failed_count += 1
                failed_permissions.append(f"Permission ID {permission_id} not found")
        except Exception as e:
            failed_count += 1
            failed_permissions.append(f"Permission ID {permission_id}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return BulkPermissionResponse(
            success_count=0,
            failed_count=len(bulk_operation.permission_ids),
            total_requested=len(bulk_operation.permission_ids),
            message="Bulk operation failed",
            failed_permissions=[f"Database error: {str(e)}"],
        )

    return BulkPermissionResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(bulk_operation.permission_ids),
        message=f"Bulk delete completed: {success_count} successful, {failed_count} failed",
        failed_permissions=failed_permissions if failed_permissions else None,
    )


@router.delete("/{permission_id}", summary="Delete permission")
@require_role("Admin")
def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    db.delete(permission)
    db.commit()

    return {"message": "Permission deleted successfully"}


@router.post(
    "/roles/{role_id}/assign",
    response_model=RolePermissionResponse,
    summary="Assign permissions to role",
)
def assign_permissions_to_role(
    role_id: int,
    assignment: RolePermissionAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = Permission.get_by_slugs(db, assignment.permission_slugs)

    if len(permissions) != len(assignment.permission_slugs):
        found_slugs = [p.slug for p in permissions]
        missing_slugs = [
            slug for slug in assignment.permission_slugs if slug not in found_slugs
        ]
        raise HTTPException(
            status_code=404, detail=f"Permissions not found: {', '.join(missing_slugs)}"
        )

    for permission in permissions:
        if permission not in role.permissions:
            role.permissions.append(permission)

    db.commit()
    db.refresh(role)

    return RolePermissionResponse(
        role_id=role.id,
        role_name=role.name,
        role_slug=role.slug,
        permissions=role.permissions,
        total_permissions=len(role.permissions),
    )


@router.post(
    "/roles/{role_id}/unassign",
    response_model=RolePermissionResponse,
    summary="Unassign permissions from role",
)
def unassign_permissions_from_role(
    role_id: int,
    unassignment: RolePermissionUnassign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = Permission.get_by_slugs(db, unassignment.permission_slugs)

    for permission in permissions:
        if permission in role.permissions:
            role.permissions.remove(permission)

    db.commit()
    db.refresh(role)

    return RolePermissionResponse(
        role_id=role.id,
        role_name=role.name,
        role_slug=role.slug,
        permissions=role.permissions,
        total_permissions=len(role.permissions),
    )


@router.get(
    "/roles/{role_id}/permissions",
    response_model=RolePermissionResponse,
    summary="Get role permissions",
)
def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return RolePermissionResponse(
        role_id=role.id,
        role_name=role.name,
        role_slug=role.slug,
        permissions=role.permissions,
        total_permissions=len(role.permissions),
    )


@router.get(
    "/users/{user_id}/check/{permission_slug}",
    response_model=UserPermissionResponse,
    summary="Check user permission",
)
def check_user_permission(
    user_id: int,
    permission_slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    permission = Permission.get_by_slug(db, permission_slug)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    granted_via_roles = []
    has_permission = False

    for role in user.roles:
        if permission in role.permissions:
            has_permission = True
            granted_via_roles.append(role.name)

    return UserPermissionResponse(
        user_id=user.id,
        permission_slug=permission_slug,
        has_permission=has_permission,
        granted_via_roles=granted_via_roles,
    )


@router.get(
    "/users/{user_id}/permissions",
    response_model=List[PermissionResponse],
    summary="Get user permissions",
)
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_permissions = set()
    for role in user.roles:
        for permission in role.permissions:
            user_permissions.add(permission)

    return list(user_permissions)
