from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
import re


class PermissionBase(BaseModel):
    slug: str = Field(
        ...,
        min_length=2,
        max_length=191,
        description="Permission slug (unique identifier)",
    )
    description: Optional[str] = Field(
        None, max_length=191, description="Permission description"
    )

    @field_validator("slug")
    def validate_slug(cls, v):
        if not v:
            raise ValueError("Slug cannot be empty")
        if not re.match(r"^[a-z0-9_.-]+$", v):
            raise ValueError(
                "Slug can only contain lowercase letters, numbers, hyphens, underscores, and dots"
            )
        return v


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    slug: Optional[str] = Field(None, min_length=2, max_length=191)
    description: Optional[str] = Field(None, max_length=191)

    @field_validator("slug")
    def validate_slug(cls, v):
        if v is not None:
            if not v:
                raise ValueError("Slug cannot be empty")
            if not re.match(r"^[a-z0-9_.-]+$", v):
                raise ValueError(
                    "Slug can only contain lowercase letters, numbers, hyphens, underscores, and dots"
                )
        return v


class PermissionResponse(PermissionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PermissionListResponse(BaseModel):
    permissions: List[PermissionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class PermissionSearchResponse(BaseModel):
    permissions: List[PermissionResponse]
    total: int
    search_term: str
    page: int
    per_page: int
    total_pages: int


class RolePermissionAssign(BaseModel):
    permission_slugs: List[str] = Field(
        ..., min_items=1, description="List of permission slugs to assign"
    )

    @field_validator("permission_slugs")
    def validate_permission_slugs(cls, v):
        if not v:
            raise ValueError("At least one permission slug is required")
        seen = set()
        unique_slugs = []
        for slug in v:
            if slug not in seen:
                seen.add(slug)
                unique_slugs.append(slug)
        return unique_slugs


class RolePermissionUnassign(BaseModel):
    permission_slugs: List[str] = Field(
        ..., min_items=1, description="List of permission slugs to unassign"
    )

    @field_validator("permission_slugs")
    def validate_permission_slugs(cls, v):
        if not v:
            raise ValueError("At least one permission slug is required")
        seen = set()
        unique_slugs = []
        for slug in v:
            if slug not in seen:
                seen.add(slug)
                unique_slugs.append(slug)
        return unique_slugs


class RolePermissionResponse(BaseModel):
    role_id: int
    role_name: str
    role_slug: str
    permissions: List[PermissionResponse]
    total_permissions: int

    class Config:
        from_attributes = True


class BulkPermissionOperation(BaseModel):
    permission_ids: List[int] = Field(
        ..., min_items=1, description="List of permission IDs"
    )

    @field_validator("permission_ids")
    def validate_permission_ids(cls, v):
        if not v:
            raise ValueError("At least one permission ID is required")
        seen = set()
        unique_ids = []
        for id in v:
            if id not in seen:
                seen.add(id)
                unique_ids.append(id)
        return unique_ids


class BulkPermissionResponse(BaseModel):
    success_count: int
    failed_count: int
    total_requested: int
    message: str
    failed_permissions: Optional[List[str]] = None


class UserPermissionCheck(BaseModel):
    user_id: int
    permission_slug: str

    class Config:
        from_attributes = True


class UserPermissionResponse(BaseModel):
    user_id: int
    permission_slug: str
    has_permission: bool
    granted_via_roles: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True
