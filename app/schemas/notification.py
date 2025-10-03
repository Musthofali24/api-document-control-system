from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import json
import uuid


class NotificationBase(BaseModel):
    type: str = Field(
        ..., min_length=1, max_length=255, description="Notification type"
    )
    notifiable_type: str = Field(
        default="App\\Models\\User",
        max_length=255,
        description="Type of notifiable entity",
    )
    notifiable_id: int = Field(
        ..., description="ID of the user who receives notification"
    )
    data: Union[str, Dict[str, Any]] = Field(
        ..., description="Notification data as JSON string or dict"
    )

    @field_validator("data")
    def validate_data(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        elif isinstance(v, str):
            try:
                json.loads(v)
                return v
            except json.JSONDecodeError:
                raise ValueError("Data must be valid JSON string")
        else:
            raise ValueError("Data must be either dict or JSON string")


class NotificationCreate(NotificationBase):

    id: Optional[str] = Field(
        default=None,
        description="UUID for notification (auto-generated if not provided)",
    )

    @field_validator("id", mode="before")
    @classmethod
    def set_id(cls, v):
        return v or str(uuid.uuid4())


class NotificationUpdate(BaseModel):

    type: Optional[str] = Field(None, min_length=1, max_length=255)
    data: Optional[Union[str, Dict[str, Any]]] = None
    read_at: Optional[datetime] = None

    @field_validator("data")
    @classmethod
    def validate_data(cls, v):
        if v is not None:
            if isinstance(v, dict):
                return json.dumps(v)
            elif isinstance(v, str):
                try:
                    json.loads(v)
                    return v
                except json.JSONDecodeError:
                    raise ValueError("Data must be valid JSON string")
            else:
                raise ValueError("Data must be either dict or JSON string")
        return v


class NotificationResponse(BaseModel):
    id: str
    type: str
    notifiable_type: str
    notifiable_id: int
    data: str
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_read: bool

    @field_validator("data", mode="before")
    @classmethod
    def parse_data(cls, v):
        if isinstance(v, dict):
            return json.dumps(v)
        return v

    class Config:
        from_attributes = True


class NotificationWithParsedData(NotificationResponse):
    parsed_data: Dict[str, Any]

    @model_validator(mode="after")
    def parse_json_data(self):
        try:
            self.parsed_data = json.loads(self.data)
        except json.JSONDecodeError:
            self.parsed_data = {}
        return self


class NotificationListResponse(BaseModel):

    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    page: int
    per_page: int
    total_pages: int


class NotificationStatsResponse(BaseModel):

    total_notifications: int
    unread_notifications: int
    read_notifications: int
    notifications_by_type: Dict[str, int]


class BulkNotificationMarkRead(BaseModel):

    notification_ids: List[str] = Field(
        ..., min_items=1, description="List of notification IDs to mark as read"
    )

    @field_validator("notification_ids")
    @classmethod
    def validate_notification_ids(cls, v):
        if not v:
            raise ValueError("At least one notification ID is required")
        seen = set()
        unique_ids = []
        for id in v:
            if id not in seen:
                seen.add(id)
                unique_ids.append(id)
        return unique_ids


class BulkNotificationDelete(BaseModel):

    notification_ids: List[str] = Field(
        ..., min_items=1, description="List of notification IDs to delete"
    )

    @field_validator("notification_ids")
    @classmethod
    def validate_notification_ids(cls, v):
        if not v:
            raise ValueError("At least one notification ID is required")
        seen = set()
        unique_ids = []
        for id in v:
            if id not in seen:
                seen.add(id)
                unique_ids.append(id)
        return unique_ids


class BulkOperationResponse(BaseModel):

    success_count: int
    failed_count: int
    total_requested: int
    message: str
    failed_items: Optional[List[str]] = None


class NotificationSend(BaseModel):

    user_id: int = Field(..., description="User ID to send notification to")
    type: str = Field(
        ..., min_length=1, max_length=255, description="Notification type"
    )
    title: str = Field(..., min_length=1, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message")
    action_url: Optional[str] = Field(None, description="URL for notification action")
    additional_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional notification data"
    )

    def to_notification_data(self) -> Dict[str, Any]:
        data = {
            "title": self.title,
            "message": self.message,
        }
        if self.action_url:
            data["action_url"] = self.action_url
        if self.additional_data:
            data.update(self.additional_data)
        return data


class BulkNotificationSend(BaseModel):

    user_ids: List[int] = Field(
        ..., min_items=1, description="List of user IDs to send notification to"
    )
    type: str = Field(
        ..., min_length=1, max_length=255, description="Notification type"
    )
    title: str = Field(..., min_length=1, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message")
    action_url: Optional[str] = Field(None, description="URL for notification action")
    additional_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional notification data"
    )

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, v):
        if not v:
            raise ValueError("At least one user ID is required")
        seen = set()
        unique_ids = []
        for id in v:
            if id not in seen:
                seen.add(id)
                unique_ids.append(id)
        return unique_ids

    def to_notification_data(self) -> Dict[str, Any]:
        data = {
            "title": self.title,
            "message": self.message,
        }
        if self.action_url:
            data["action_url"] = self.action_url
        if self.additional_data:
            data.update(self.additional_data)
        return data


# Filter schemas
class NotificationFilter(BaseModel):

    user_id: Optional[int] = None
    type: Optional[str] = None
    is_read: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class NotificationMarkAsRead(BaseModel):

    is_read: bool = Field(
        default=True, description="Mark as read (true) or unread (false)"
    )


class NotificationPreferences(BaseModel):
    """Schema untuk user notification preferences"""

    user_id: int
    email_notifications: bool = True
    push_notifications: bool = True
    notification_types: Dict[str, bool] = Field(default_factory=dict)

    class Config:
        from_attributes = True
