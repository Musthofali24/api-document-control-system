"""
Helper functions untuk notification system
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
import json
import uuid
from datetime import datetime

from app.models.user import User
from app.models.notification import Notification


class NotificationHelper:
    """Helper class untuk notification operations"""

    @staticmethod
    def create_notification(
        db: Session,
        user_id: int,
        type: str,
        data: Union[Dict[str, Any], str],
        notifiable_type: str = "App\\Models\\User",
    ) -> Notification:
        """
        Create a single notification

        Args:
            db: Database session
            user_id: Target user ID
            type: Notification type
            data: Notification data (dict or JSON string)
            notifiable_type: Type of notifiable entity

        Returns:
            Created Notification object
        """
        # Convert data to JSON string if it's a dict
        if isinstance(data, dict):
            data_str = json.dumps(data)
        else:
            data_str = str(data)

        notification = Notification(
            id=str(uuid.uuid4()),
            type=type,
            notifiable_type=notifiable_type,
            notifiable_id=user_id,
            data=data_str,
        )

        db.add(notification)
        return notification

    @staticmethod
    def send_notification(
        db: Session,
        user_id: int,
        type: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Send a notification to a user with structured data

        Args:
            db: Database session
            user_id: Target user ID
            type: Notification type
            title: Notification title
            message: Notification message
            action_url: Optional URL for action
            additional_data: Optional additional data

        Returns:
            Created Notification object
        """
        # Build notification data
        data = {
            "title": title,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if action_url:
            data["action_url"] = action_url

        if additional_data:
            data.update(additional_data)

        return NotificationHelper.create_notification(
            db=db, user_id=user_id, type=type, data=data
        )

    @staticmethod
    def send_bulk_notification(
        db: Session,
        user_ids: List[int],
        type: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> List[Notification]:
        """
        Send notification to multiple users

        Args:
            db: Database session
            user_ids: List of target user IDs
            type: Notification type
            title: Notification title
            message: Notification message
            action_url: Optional URL for action
            additional_data: Optional additional data

        Returns:
            List of created Notification objects
        """
        notifications = []

        for user_id in user_ids:
            notification = NotificationHelper.send_notification(
                db=db,
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                action_url=action_url,
                additional_data=additional_data,
            )
            notifications.append(notification)

        return notifications

    @staticmethod
    def notify_document_created(
        db: Session,
        user_id: int,
        document_title: str,
        document_id: int,
        created_by_name: str,
    ) -> Notification:
        """
        Send notification when a new document is created

        Args:
            db: Database session
            user_id: User to notify
            document_title: Title of the created document
            document_id: ID of the created document
            created_by_name: Name of user who created the document

        Returns:
            Created Notification object
        """
        return NotificationHelper.send_notification(
            db=db,
            user_id=user_id,
            type="document_created",
            title="New Document Created",
            message=f"Document '{document_title}' has been created by {created_by_name}",
            action_url=f"/documents/{document_id}",
            additional_data={
                "document_id": document_id,
                "document_title": document_title,
                "created_by": created_by_name,
            },
        )

    @staticmethod
    def notify_document_approved(
        db: Session,
        user_id: int,
        document_title: str,
        document_id: int,
        approved_by_name: str,
    ) -> Notification:
        """
        Send notification when a document is approved

        Args:
            db: Database session
            user_id: User to notify (usually document creator)
            document_title: Title of the approved document
            document_id: ID of the approved document
            approved_by_name: Name of user who approved the document

        Returns:
            Created Notification object
        """
        return NotificationHelper.send_notification(
            db=db,
            user_id=user_id,
            type="document_approved",
            title="Document Approved",
            message=f"Your document '{document_title}' has been approved by {approved_by_name}",
            action_url=f"/documents/{document_id}",
            additional_data={
                "document_id": document_id,
                "document_title": document_title,
                "approved_by": approved_by_name,
            },
        )

    @staticmethod
    def notify_document_rejected(
        db: Session,
        user_id: int,
        document_title: str,
        document_id: int,
        rejected_by_name: str,
        reason: Optional[str] = None,
    ) -> Notification:
        """
        Send notification when a document is rejected

        Args:
            db: Database session
            user_id: User to notify (usually document creator)
            document_title: Title of the rejected document
            document_id: ID of the rejected document
            rejected_by_name: Name of user who rejected the document
            reason: Optional rejection reason

        Returns:
            Created Notification object
        """
        message = (
            f"Your document '{document_title}' has been rejected by {rejected_by_name}"
        )
        if reason:
            message += f". Reason: {reason}"

        additional_data = {
            "document_id": document_id,
            "document_title": document_title,
            "rejected_by": rejected_by_name,
        }

        if reason:
            additional_data["rejection_reason"] = reason

        return NotificationHelper.send_notification(
            db=db,
            user_id=user_id,
            type="document_rejected",
            title="Document Rejected",
            message=message,
            action_url=f"/documents/{document_id}",
            additional_data=additional_data,
        )

    @staticmethod
    def notify_user_created(
        db: Session,
        user_id: int,
        new_user_name: str,
        new_user_email: str,
        created_by_name: str,
    ) -> Notification:
        """
        Send notification when a new user is created

        Args:
            db: Database session
            user_id: User to notify (usually admin)
            new_user_name: Name of the new user
            new_user_email: Email of the new user
            created_by_name: Name of user who created the account

        Returns:
            Created Notification object
        """
        return NotificationHelper.send_notification(
            db=db,
            user_id=user_id,
            type="user_created",
            title="New User Created",
            message=f"New user '{new_user_name}' ({new_user_email}) has been created by {created_by_name}",
            action_url=f"/users",
            additional_data={
                "new_user_name": new_user_name,
                "new_user_email": new_user_email,
                "created_by": created_by_name,
            },
        )

    @staticmethod
    def notify_role_assigned(
        db: Session, user_id: int, role_name: str, assigned_by_name: str
    ) -> Notification:
        """
        Send notification when a role is assigned to user

        Args:
            db: Database session
            user_id: User who got the role assigned
            role_name: Name of the assigned role
            assigned_by_name: Name of user who assigned the role

        Returns:
            Created Notification object
        """
        return NotificationHelper.send_notification(
            db=db,
            user_id=user_id,
            type="role_assigned",
            title="Role Assigned",
            message=f"You have been assigned the '{role_name}' role by {assigned_by_name}",
            action_url=f"/profile",
            additional_data={
                "role_name": role_name,
                "assigned_by": assigned_by_name,
            },
        )

    @staticmethod
    def notify_permission_granted(
        db: Session, user_id: int, permission_name: str, granted_by_name: str
    ) -> Notification:
        """
        Send notification when a permission is granted to user

        Args:
            db: Database session
            user_id: User who got the permission
            permission_name: Name of the granted permission
            granted_by_name: Name of user who granted the permission

        Returns:
            Created Notification object
        """
        return NotificationHelper.send_notification(
            db=db,
            user_id=user_id,
            type="permission_granted",
            title="Permission Granted",
            message=f"You have been granted the '{permission_name}' permission by {granted_by_name}",
            action_url=f"/profile",
            additional_data={
                "permission_name": permission_name,
                "granted_by": granted_by_name,
            },
        )

    @staticmethod
    def notify_system_maintenance(
        db: Session,
        user_ids: List[int],
        maintenance_start: datetime,
        maintenance_end: datetime,
        description: Optional[str] = None,
    ) -> List[Notification]:
        """
        Send system maintenance notification to multiple users

        Args:
            db: Database session
            user_ids: List of users to notify
            maintenance_start: Maintenance start datetime
            maintenance_end: Maintenance end datetime
            description: Optional maintenance description

        Returns:
            List of created Notification objects
        """
        message = f"System maintenance scheduled from {maintenance_start.strftime('%Y-%m-%d %H:%M')} to {maintenance_end.strftime('%Y-%m-%d %H:%M')}"
        if description:
            message += f". {description}"

        return NotificationHelper.send_bulk_notification(
            db=db,
            user_ids=user_ids,
            type="system_maintenance",
            title="System Maintenance Scheduled",
            message=message,
            additional_data={
                "maintenance_start": maintenance_start.isoformat(),
                "maintenance_end": maintenance_end.isoformat(),
                "description": description,
            },
        )

    @staticmethod
    def get_user_unread_count(db: Session, user_id: int) -> int:
        """
        Get unread notification count for a user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of unread notifications
        """
        return Notification.count_unread_by_user(db, user_id)

    @staticmethod
    def mark_all_read_for_user(db: Session, user_id: int) -> int:
        """
        Mark all notifications as read for a user

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        return Notification.mark_all_read_by_user(db, user_id)

    @staticmethod
    def delete_old_notifications(
        db: Session, days_old: int = 30, only_read: bool = True
    ) -> int:
        """
        Delete old notifications (maintenance helper)

        Args:
            db: Database session
            days_old: Delete notifications older than this many days
            only_read: Only delete read notifications if True

        Returns:
            Number of notifications deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        query = db.query(Notification).filter(Notification.created_at < cutoff_date)

        if only_read:
            query = query.filter(Notification.read_at.is_not(None))

        count = query.count()
        query.delete()

        return count
