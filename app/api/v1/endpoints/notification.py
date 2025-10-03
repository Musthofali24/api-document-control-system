from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import math
import json
import uuid

from app.core.auth import get_current_user
from app.config.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate,
    NotificationUpdate,
    NotificationResponse,
    NotificationWithParsedData,
    NotificationListResponse,
    NotificationStatsResponse,
    BulkNotificationMarkRead,
    BulkNotificationDelete,
    BulkOperationResponse,
    NotificationSend,
    BulkNotificationSend,
    NotificationFilter,
    NotificationMarkAsRead,
)

router = APIRouter()


@router.post(
    "/", response_model=NotificationResponse, summary="Create new notification"
)
def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new notification.

    - **type**: Notification type (e.g., 'document_approved', 'user_created')
    - **notifiable_id**: User ID who will receive the notification
    - **data**: Notification data as JSON object or string
    """
    # Verify target user exists
    target_user = db.query(User).filter(User.id == notification.notifiable_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    db_notification = Notification(
        id=notification.id,
        type=notification.type,
        notifiable_type=notification.notifiable_type,
        notifiable_id=notification.notifiable_id,
        data=notification.data,
    )

    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    return db_notification


@router.get(
    "/my",
    response_model=NotificationListResponse,
    summary="Get current user's notifications",
)
def get_my_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    is_read: Optional[bool] = Query(
        None, description="Filter by read status (true/false)"
    ),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's notifications with pagination and filters.

    - **page**: Page number (starts from 1)
    - **per_page**: Number of items per page (1-100)
    - **is_read**: Filter by read status (optional)
    - **type**: Filter by notification type (optional)
    """
    skip = (page - 1) * per_page

    query = db.query(Notification).filter(Notification.notifiable_id == current_user.id)

    # Apply filters
    if is_read is not None:
        if is_read:
            query = query.filter(Notification.read_at.is_not(None))
        else:
            query = query.filter(Notification.read_at.is_(None))

    if type:
        query = query.filter(Notification.type == type)

    # Get notifications dengan pagination
    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(per_page)
        .all()
    )

    # Count total dan unread
    total = query.count()
    unread_count = Notification.count_unread_by_user(db, current_user.id)
    total_pages = math.ceil(total / per_page)

    return NotificationListResponse(
        notifications=notifications,
        total=total,
        unread_count=unread_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get(
    "/users/{user_id}",
    response_model=NotificationListResponse,
    summary="Get user's notifications (admin)",
)
def get_user_notifications(
    user_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get notifications for specific user (admin only).

    - **user_id**: Target user ID
    - **page**: Page number (starts from 1)
    - **per_page**: Number of items per page (1-100)
    - **is_read**: Filter by read status (optional)
    - **type**: Filter by notification type (optional)
    """
    # Verify target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    skip = (page - 1) * per_page

    query = db.query(Notification).filter(Notification.notifiable_id == user_id)

    # Apply filters
    if is_read is not None:
        if is_read:
            query = query.filter(Notification.read_at.is_not(None))
        else:
            query = query.filter(Notification.read_at.is_(None))

    if type:
        query = query.filter(Notification.type == type)

    # Get notifications dengan pagination
    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(per_page)
        .all()
    )

    # Count total dan unread
    total = query.count()
    unread_count = Notification.count_unread_by_user(db, user_id)
    total_pages = math.ceil(total / per_page)

    return NotificationListResponse(
        notifications=notifications,
        total=total,
        unread_count=unread_count,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get(
    "/my/stats",
    response_model=NotificationStatsResponse,
    summary="Get current user's notification stats",
)
def get_my_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's notification statistics.
    """
    total = Notification.count_by_user(db, current_user.id)
    unread = Notification.count_unread_by_user(db, current_user.id)
    read = total - unread

    # Get notifications by type count
    notifications_by_type = {}
    type_results = (
        db.query(Notification.type, db.func.count(Notification.id))
        .filter(Notification.notifiable_id == current_user.id)
        .group_by(Notification.type)
        .all()
    )

    for type_name, count in type_results:
        notifications_by_type[type_name] = count

    return NotificationStatsResponse(
        total_notifications=total,
        unread_notifications=unread,
        read_notifications=read,
        notifications_by_type=notifications_by_type,
    )


@router.get(
    "/{notification_id}",
    response_model=NotificationWithParsedData,
    summary="Get notification by ID",
)
def get_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a notification by ID. Users can only access their own notifications.

    - **notification_id**: The ID of the notification to retrieve
    """
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Check if user owns this notification
    if notification.notifiable_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Parse JSON data
    try:
        parsed_data = json.loads(notification.data)
    except json.JSONDecodeError:
        parsed_data = {}

    return NotificationWithParsedData(
        **notification.to_dict(), parsed_data=parsed_data, is_read=notification.is_read
    )


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read/unread",
)
def mark_notification_read(
    notification_id: str,
    mark_read: NotificationMarkAsRead = NotificationMarkAsRead(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a notification as read or unread.

    - **notification_id**: The ID of the notification
    - **is_read**: True to mark as read, False to mark as unread
    """
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Check if user owns this notification
    if notification.notifiable_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if mark_read.is_read:
        notification.mark_as_read()
    else:
        notification.mark_as_unread()

    db.commit()
    db.refresh(notification)

    return notification


@router.put("/my/mark-all-read", summary="Mark all notifications as read")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark all current user's notifications as read.
    """
    updated_count = Notification.mark_all_read_by_user(db, current_user.id)
    db.commit()

    return {"message": f"Marked {updated_count} notifications as read"}


@router.delete("/{notification_id}", summary="Delete notification")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a notification. Users can only delete their own notifications.

    - **notification_id**: The ID of the notification to delete
    """
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Check if user owns this notification
    if notification.notifiable_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.delete(notification)
    db.commit()

    return {"message": "Notification deleted successfully"}


@router.delete("/my/read", summary="Delete all read notifications")
def delete_read_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete all read notifications for current user.
    """
    deleted_count = Notification.delete_read_by_user(db, current_user.id)
    db.commit()

    return {"message": f"Deleted {deleted_count} read notifications"}


# Bulk operations
@router.put(
    "/bulk/mark-read",
    response_model=BulkOperationResponse,
    summary="Bulk mark notifications as read",
)
def bulk_mark_notifications_read(
    bulk_request: BulkNotificationMarkRead,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark multiple notifications as read.

    - **notification_ids**: List of notification IDs to mark as read
    """
    success_count = 0
    failed_count = 0
    failed_items = []

    for notification_id in bulk_request.notification_ids:
        try:
            notification = (
                db.query(Notification)
                .filter(Notification.id == notification_id)
                .first()
            )
            if notification and notification.notifiable_id == current_user.id:
                notification.mark_as_read()
                success_count += 1
            else:
                failed_count += 1
                failed_items.append(
                    f"Notification {notification_id} not found or access denied"
                )
        except Exception as e:
            failed_count += 1
            failed_items.append(f"Notification {notification_id}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return BulkOperationResponse(
            success_count=0,
            failed_count=len(bulk_request.notification_ids),
            total_requested=len(bulk_request.notification_ids),
            message="Bulk operation failed",
            failed_items=[f"Database error: {str(e)}"],
        )

    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(bulk_request.notification_ids),
        message=f"Bulk mark read completed: {success_count} successful, {failed_count} failed",
        failed_items=failed_items if failed_items else None,
    )


@router.delete(
    "/bulk", response_model=BulkOperationResponse, summary="Bulk delete notifications"
)
def bulk_delete_notifications(
    bulk_request: BulkNotificationDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete multiple notifications.

    - **notification_ids**: List of notification IDs to delete
    """
    success_count = 0
    failed_count = 0
    failed_items = []

    for notification_id in bulk_request.notification_ids:
        try:
            notification = (
                db.query(Notification)
                .filter(Notification.id == notification_id)
                .first()
            )
            if notification and notification.notifiable_id == current_user.id:
                db.delete(notification)
                success_count += 1
            else:
                failed_count += 1
                failed_items.append(
                    f"Notification {notification_id} not found or access denied"
                )
        except Exception as e:
            failed_count += 1
            failed_items.append(f"Notification {notification_id}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return BulkOperationResponse(
            success_count=0,
            failed_count=len(bulk_request.notification_ids),
            total_requested=len(bulk_request.notification_ids),
            message="Bulk operation failed",
            failed_items=[f"Database error: {str(e)}"],
        )

    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(bulk_request.notification_ids),
        message=f"Bulk delete completed: {success_count} successful, {failed_count} failed",
        failed_items=failed_items if failed_items else None,
    )


# Send notification endpoints
@router.post(
    "/send", response_model=NotificationResponse, summary="Send notification to user"
)
def send_notification(
    notification_send: NotificationSend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a notification to a user.

    - **user_id**: User ID to send notification to
    - **type**: Notification type
    - **title**: Notification title
    - **message**: Notification message
    - **action_url**: Optional action URL
    - **additional_data**: Optional additional data
    """
    # Verify target user exists
    target_user = db.query(User).filter(User.id == notification_send.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    # Create notification data
    notification_data = notification_send.to_notification_data()

    db_notification = Notification(
        id=str(uuid.uuid4()),
        type=notification_send.type,
        notifiable_type="App\\Models\\User",
        notifiable_id=notification_send.user_id,
        data=json.dumps(notification_data),
    )

    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    return db_notification


@router.post(
    "/send/bulk",
    response_model=BulkOperationResponse,
    summary="Send notification to multiple users",
)
def send_bulk_notification(
    bulk_notification_send: BulkNotificationSend,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a notification to multiple users.

    - **user_ids**: List of user IDs to send notification to
    - **type**: Notification type
    - **title**: Notification title
    - **message**: Notification message
    - **action_url**: Optional action URL
    - **additional_data**: Optional additional data
    """
    success_count = 0
    failed_count = 0
    failed_items = []

    # Create notification data
    notification_data = bulk_notification_send.to_notification_data()

    for user_id in bulk_notification_send.user_ids:
        try:
            # Verify user exists
            target_user = db.query(User).filter(User.id == user_id).first()
            if not target_user:
                failed_count += 1
                failed_items.append(f"User ID {user_id} not found")
                continue

            # Create notification
            db_notification = Notification(
                id=str(uuid.uuid4()),
                type=bulk_notification_send.type,
                notifiable_type="App\\Models\\User",
                notifiable_id=user_id,
                data=json.dumps(notification_data),
            )

            db.add(db_notification)
            success_count += 1

        except Exception as e:
            failed_count += 1
            failed_items.append(f"User ID {user_id}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return BulkOperationResponse(
            success_count=0,
            failed_count=len(bulk_notification_send.user_ids),
            total_requested=len(bulk_notification_send.user_ids),
            message="Bulk notification send failed",
            failed_items=[f"Database error: {str(e)}"],
        )

    return BulkOperationResponse(
        success_count=success_count,
        failed_count=failed_count,
        total_requested=len(bulk_notification_send.user_ids),
        message=f"Bulk notification send completed: {success_count} successful, {failed_count} failed",
        failed_items=failed_items if failed_items else None,
    )
