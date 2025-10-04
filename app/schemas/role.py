from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from app.schemas.user import UserResponse


class RoleBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator("slug")
    def slug_must_be_lowercase(cls, v):
        if not v or not v.strip():
            raise ValueError("Slug cannot be empty")
        return v.lower().replace(" ", "-")


class RoleCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None

    @validator("name")
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator("slug", pre=True, always=True)
    def generate_slug(cls, v, values):
        if v:
            return v.lower().replace(" ", "-")
        # Auto-generate slug from name
        name = values.get("name", "")
        if name:
            return name.lower().replace(" ", "-")
        return ""


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None

    @validator("slug")
    def slug_must_be_lowercase(cls, v):
        if v:
            return v.lower().replace(" ", "-")
        return v


class RoleResponse(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserRoleAssign(BaseModel):
    user_id: int
    role_id: int


class UserRoleUnassign(BaseModel):
    user_id: int
    role_id: int


class UserWithRoles(BaseModel):
    id: int
    name: str
    email: str
    roles: List[RoleResponse] = []

    class Config:
        from_attributes = True


class RoleWithUsers(RoleResponse):
    users: List["UserResponse"] = []

    class Config:
        from_attributes = True


class BulkRoleAssign(BaseModel):
    user_ids: List[int]
    role_id: int


class BulkRoleUnassign(BaseModel):
    user_ids: List[int]
    role_id: int


class UserRoleCheck(BaseModel):
    user_id: int
    role_name: str
    role_slug: str
    has_role: bool
