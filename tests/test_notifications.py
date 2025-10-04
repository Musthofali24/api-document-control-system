"""
Tests for Notification endpoints
"""

import pytest
import json
import uuid
from fastapi import status

from app.models.notification import Notification
from app.models.user import User
from tests.conftest import TEST_NOTIFICATION_DATA, create_test_notification


class TestNotificationEndpoints:
    """Test class for Notification API endpoints"""

    def test_create_notification_success(self, client, authenticated_admin, test_user):
        """Test successful notification creation"""
        notification_data = {
            "type": "test_notification",
            "notifiable_id": test_user.id,
            "data": {"title": "Test", "message": "Test message"},
        }

        response = client.post(
            "/api/v1/notifications/",
            json=notification_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["type"] == notification_data["type"]
        assert data["notifiable_id"] == notification_data["notifiable_id"]
        assert "id" in data

    def test_create_notification_user_not_found(self, client, authenticated_admin):
        """Test notification creation for non-existent user fails"""
        notification_data = {
            "type": "test_notification",
            "notifiable_id": 999999,
            "data": {"title": "Test", "message": "Test message"},
        }

        response = client.post(
            "/api/v1/notifications/",
            json=notification_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Target user not found" in response.json()["detail"]

    def test_get_my_notifications(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test getting current user's notifications"""
        # Create test notifications
        for i in range(3):
            create_test_notification(db_session, test_user.id, f"type_{i}")

        response = client.get(
            "/api/v1/notifications/my?page=1&per_page=10",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "notifications" in data
        assert "total" in data
        assert "unread_count" in data
        assert len(data["notifications"]) == 3

    def test_get_my_notifications_filtered_by_read_status(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test getting notifications filtered by read status"""
        # Create notifications
        notif1 = create_test_notification(db_session, test_user.id, "type_1")
        notif2 = create_test_notification(db_session, test_user.id, "type_2")

        # Mark one as read
        notif1.mark_as_read()
        db_session.commit()

        # Get unread notifications
        response = client.get(
            "/api/v1/notifications/my?is_read=false",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["id"] == notif2.id

    def test_get_my_notifications_filtered_by_type(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test getting notifications filtered by type"""
        # Create notifications with different types
        create_test_notification(db_session, test_user.id, "document_approved")
        create_test_notification(db_session, test_user.id, "user_created")
        create_test_notification(db_session, test_user.id, "document_approved")

        response = client.get(
            "/api/v1/notifications/my?type=document_approved",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["notifications"]) == 2

    def test_get_user_notifications_admin(
        self, client, authenticated_admin, test_user, db_session
    ):
        """Test admin getting specific user's notifications"""
        create_test_notification(db_session, test_user.id, "admin_test")

        response = client.get(
            f"/api/v1/notifications/users/{test_user.id}?page=1&per_page=10",
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["notifications"]) == 1

    def test_get_user_notifications_user_not_found(self, client, authenticated_admin):
        """Test getting notifications for non-existent user"""
        response = client.get(
            "/api/v1/notifications/users/999999", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_notification_stats(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test getting notification statistics"""
        # Create mixed notifications
        notif1 = create_test_notification(db_session, test_user.id, "document_approved")
        notif2 = create_test_notification(db_session, test_user.id, "user_created")
        create_test_notification(db_session, test_user.id, "document_approved")

        # Mark one as read
        notif1.mark_as_read()
        db_session.commit()

        response = client.get(
            "/api/v1/notifications/my/stats", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_notifications"] == 3
        assert data["unread_notifications"] == 2
        assert data["read_notifications"] == 1
        assert data["notifications_by_type"]["document_approved"] == 2
        assert data["notifications_by_type"]["user_created"] == 1

    def test_get_notification_by_id_success(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test getting notification by ID"""
        notification = create_test_notification(db_session, test_user.id)

        response = client.get(
            f"/api/v1/notifications/{notification.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == notification.id
        assert "parsed_data" in data

    def test_get_notification_by_id_access_denied(
        self, client, authenticated_user, admin_user, db_session
    ):
        """Test user cannot access other user's notifications"""
        # Create notification for admin user
        notification = create_test_notification(db_session, admin_user.id)

        response = client.get(
            f"/api/v1/notifications/{notification.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_mark_notification_as_read(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test marking notification as read"""
        notification = create_test_notification(db_session, test_user.id)

        response = client.put(
            f"/api/v1/notifications/{notification.id}/read",
            json={"is_read": True},
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["read_at"] is not None

    def test_mark_notification_as_unread(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test marking notification as unread"""
        notification = create_test_notification(db_session, test_user.id)
        notification.mark_as_read()
        db_session.commit()

        response = client.put(
            f"/api/v1/notifications/{notification.id}/read",
            json={"is_read": False},
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["read_at"] is None

    def test_mark_all_notifications_read(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test marking all notifications as read"""
        # Create multiple notifications
        for i in range(3):
            create_test_notification(db_session, test_user.id, f"type_{i}")

        response = client.put(
            "/api/v1/notifications/my/mark-all-read",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "3 notifications" in response.json()["message"]

    def test_delete_notification_success(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test deleting notification"""
        notification = create_test_notification(db_session, test_user.id)

        response = client.delete(
            f"/api/v1/notifications/{notification.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_delete_notification_access_denied(
        self, client, authenticated_user, admin_user, db_session
    ):
        """Test user cannot delete other user's notifications"""
        notification = create_test_notification(db_session, admin_user.id)

        response = client.delete(
            f"/api/v1/notifications/{notification.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_read_notifications(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test deleting all read notifications"""
        # Create notifications
        notif1 = create_test_notification(db_session, test_user.id, "type_1")
        notif2 = create_test_notification(db_session, test_user.id, "type_2")
        create_test_notification(db_session, test_user.id, "type_3")  # Keep unread

        # Mark two as read
        notif1.mark_as_read()
        notif2.mark_as_read()
        db_session.commit()

        response = client.delete(
            "/api/v1/notifications/my/read", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        assert "2 read notifications" in response.json()["message"]

    def test_bulk_mark_notifications_read(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test bulk marking notifications as read"""
        # Create notifications
        notifications = []
        for i in range(3):
            notif = create_test_notification(db_session, test_user.id, f"type_{i}")
            notifications.append(notif)

        bulk_data = {"notification_ids": [notif.id for notif in notifications]}

        response = client.put(
            "/api/v1/notifications/bulk/mark-read",
            json=bulk_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_bulk_delete_notifications(
        self, client, authenticated_user, test_user, db_session
    ):
        """Test bulk deleting notifications"""
        # Create notifications
        notifications = []
        for i in range(3):
            notif = create_test_notification(db_session, test_user.id, f"type_{i}")
            notifications.append(notif)

        bulk_data = {"notification_ids": [notif.id for notif in notifications]}

        response = client.request(
            "DELETE",
            "/api/v1/notifications/bulk",
            json=bulk_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_send_notification_to_user(self, client, authenticated_admin, test_user):
        """Test sending notification to a user"""
        send_data = {
            "user_id": test_user.id,
            "type": "admin_message",
            "title": "Important Notice",
            "message": "This is an important message",
            "action_url": "/important-page",
        }

        response = client.post(
            "/api/v1/notifications/send",
            json=send_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["type"] == send_data["type"]
        assert data["notifiable_id"] == test_user.id

    def test_send_notification_user_not_found(self, client, authenticated_admin):
        """Test sending notification to non-existent user"""
        send_data = {
            "user_id": 999999,
            "type": "test",
            "title": "Test",
            "message": "Test message",
        }

        response = client.post(
            "/api/v1/notifications/send",
            json=send_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_send_bulk_notification(self, client, authenticated_admin, sample_users):
        """Test sending notification to multiple users"""
        user_ids = [user.id for user in sample_users[:3]]

        bulk_send_data = {
            "user_ids": user_ids,
            "type": "system_announcement",
            "title": "System Maintenance",
            "message": "System will be down for maintenance",
        }

        response = client.post(
            "/api/v1/notifications/send/bulk",
            json=bulk_send_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_send_bulk_notification_partial_fail(
        self, client, authenticated_admin, sample_users
    ):
        """Test bulk sending with some non-existent users"""
        valid_ids = [sample_users[0].id, sample_users[1].id]
        invalid_ids = [999999, 888888]
        all_ids = valid_ids + invalid_ids

        bulk_send_data = {
            "user_ids": all_ids,
            "type": "test",
            "title": "Test",
            "message": "Test message",
        }

        response = client.post(
            "/api/v1/notifications/send/bulk",
            json=bulk_send_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 2
        assert data["failed_count"] == 2

    def test_notification_data_validation(self, client, authenticated_admin, test_user):
        """Test notification data field validation"""
        # Test with dict data (should be converted to JSON string)
        notification_data = {
            "type": "test",
            "notifiable_id": test_user.id,
            "data": {"key": "value", "number": 123},
        }

        response = client.post(
            "/api/v1/notifications/",
            json=notification_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data["data"], str)  # Should be JSON string

    def test_notification_unauthorized_access(
        self, client, authenticated_user, test_user
    ):
        """Test that regular users cannot create notifications"""
        notification_data = {
            "type": "test",
            "notifiable_id": test_user.id,
            "data": {"message": "test"},
        }

        response = client.post(
            "/api/v1/notifications/",
            json=notification_data,
            headers=authenticated_user["headers"],
        )

        # Assuming regular users cannot create notifications (depends on permission system)
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_notification_id_generation(self, client, authenticated_admin, test_user):
        """Test that notification ID is auto-generated as UUID"""
        notification_data = {
            "type": "test",
            "notifiable_id": test_user.id,
            "data": {"message": "test"},
        }

        response = client.post(
            "/api/v1/notifications/",
            json=notification_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate UUID format
        try:
            uuid.UUID(data["id"])
            uuid_valid = True
        except ValueError:
            uuid_valid = False

        assert uuid_valid is True
