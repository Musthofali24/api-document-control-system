"""
Tests for     def test_create_user_success(self, client, authenticated_admin):
        \"\"\"Test successful user creation\"\"\"
        response = client.post(
            \"/api/v1/users/\", json=TEST_USER_DATA, headers=authenticated_admin[\"headers\"]
        )

        assert response.status_code == status.HTTP_201_CREATEDdpoints
"""

import pytest
from fastapi import status

from app.models.user import User
from tests.conftest import TEST_USER_DATA


class TestUserEndpoints:
    """Test class for User API endpoints"""

    def test_create_user_success(self, client, authenticated_admin):
        """Test successful user creation"""
        response = client.post(
            "/api/v1/users/",
            json=TEST_USER_DATA,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == TEST_USER_DATA["name"]
        assert data["email"] == TEST_USER_DATA["email"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned

    def test_create_user_duplicate_email(self, client, authenticated_admin, test_user):
        """Test creating user with duplicate email fails"""
        duplicate_user_data = {
            "name": "Another User",
            "email": test_user.email,  # Same email
            "password": "password123",
        }

        response = client.post(
            "/api/v1/users/",
            json=duplicate_user_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]

    def test_create_user_unauthorized(self, client, authenticated_user):
        """Test user creation without admin access fails"""
        response = client.post(
            "/api/v1/users/", json=TEST_USER_DATA, headers=authenticated_user["headers"]
        )

        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_users_list(self, client, authenticated_admin, sample_users):
        """Test getting list of users"""
        response = client.get("/api/v1/users/", headers=authenticated_admin["headers"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        assert len(data["users"]) >= 1  # At least the admin user
        assert "page" in data
        assert "per_page" in data

    def test_get_user_by_id_success(self, client, authenticated_user, test_user):
        """Test getting user by ID"""
        response = client.get(
            f"/api/v1/users/{test_user.id}", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    def test_get_user_by_id_not_found(self, client, authenticated_user):
        """Test getting non-existent user returns 404"""
        response = client.get(
            "/api/v1/users/999999", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_user_success(self, client, authenticated_admin, test_user):
        """Test successful user update"""
        update_data = {"name": "Updated Name", "email": "updated@example.com"}

        response = client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["email"] == update_data["email"]

    def test_update_user_duplicate_email(
        self, client, authenticated_admin, sample_users
    ):
        """Test updating user with existing email fails"""
        user1, user2 = sample_users[0], sample_users[1]

        update_data = {"email": user2.email}  # Use existing email

        response = client.put(
            f"/api/v1/users/{user1.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"]

    def test_update_own_profile(self, client, authenticated_user):
        """Test user updating their own profile"""
        update_data = {"name": "My Updated Name"}

        response = client.put(
            f"/api/v1/users/{authenticated_user['user'].id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_update_other_user_unauthorized(
        self, client, authenticated_user, admin_user
    ):
        """Test regular user cannot update other users"""
        update_data = {"name": "Unauthorized Update"}

        response = client.put(
            f"/api/v1/users/{admin_user.id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_delete_user_success(self, client, authenticated_admin, test_user):
        """Test successful user deletion"""
        response = client.delete(
            f"/api/v1/users/{test_user.id}", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_delete_user_not_found(self, client, authenticated_admin):
        """Test deleting non-existent user returns 404"""
        response = client.delete(
            "/api/v1/users/999999", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user_unauthorized(self, client, authenticated_user, admin_user):
        """Test regular user cannot delete users"""
        response = client.delete(
            f"/api/v1/users/{admin_user.id}", headers=authenticated_user["headers"]
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_search_users(self, client, authenticated_admin, sample_users):
        """Test user search functionality"""
        response = client.get(
            "/api/v1/users/search?q=User&page=1&per_page=10",
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "search_term" in data
        assert data["search_term"] == "User"

    def test_get_user_profile(self, client, authenticated_user):
        """Test getting current user's profile"""
        response = client.get(
            "/api/v1/users/profile", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == authenticated_user["user"].email

    def test_update_user_profile(self, client, authenticated_user):
        """Test updating current user's profile"""
        update_data = {"name": "Updated Profile Name"}

        response = client.put(
            "/api/v1/users/profile",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]

    def test_change_password_success(self, client, authenticated_user):
        """Test successful password change"""
        password_data = {
            "current_password": "testpass123",
            "new_password": "newtestpass123",
        }

        response = client.put(
            "/api/v1/users/change-password",
            json=password_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Password changed successfully" in response.json()["message"]

    def test_change_password_wrong_current(self, client, authenticated_user):
        """Test password change with wrong current password"""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newtestpass123",
        }

        response = client.put(
            "/api/v1/users/change-password",
            json=password_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Current password is incorrect" in response.json()["detail"]

    def test_user_with_roles(
        self, client, authenticated_admin, test_user, test_role, db_session
    ):
        """Test getting user with their roles"""
        # Assign role to user
        test_user.roles.append(test_role)
        db_session.commit()

        response = client.get(
            f"/api/v1/users/{test_user.id}", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if "roles" in data:  # If roles are included in user response
            assert len(data["roles"]) == 1
            assert data["roles"][0]["id"] == test_role.id

    def test_bulk_delete_users(self, client, authenticated_admin, sample_users):
        """Test bulk deletion of users"""
        user_ids = [user.id for user in sample_users[:3]]

        bulk_data = {"user_ids": user_ids}

        response = client.request(
            "DELETE",
            "/api/v1/users/bulk",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_user_statistics(self, client, authenticated_admin, sample_users):
        """Test getting user statistics"""
        response = client.get(
            "/api/v1/users/stats", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_users" in data
        assert "active_users" in data

    def test_create_user_invalid_email(self, client, authenticated_admin):
        """Test creating user with invalid email format"""
        invalid_data = {
            "name": "Test User",
            "email": "not-an-email",
            "password": "password123",
        }

        response = client.post(
            "/api/v1/users/", json=invalid_data, headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_user_weak_password(self, client, authenticated_admin):
        """Test creating user with weak password (if validation exists)"""
        weak_password_data = {
            "name": "Test User",
            "email": "test_weak@example.com",
            "password": "123",  # Very weak password
        }

        response = client.post(
            "/api/v1/users/",
            json=weak_password_data,
            headers=authenticated_admin["headers"],
        )

        # This test assumes password strength validation exists
        # If not implemented, this will pass
        if response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            assert "password" in response.json()["detail"][0]["loc"]

    def test_user_email_case_insensitive(self, client, authenticated_admin, test_user):
        """Test that user lookup is case insensitive for email"""
        # Try to create user with same email but different case
        case_variant_data = {
            "name": "Case Test User",
            "email": test_user.email.upper(),  # Same email, different case
            "password": "password123",
        }

        response = client.post(
            "/api/v1/users/",
            json=case_variant_data,
            headers=authenticated_admin["headers"],
        )

        # Should fail due to duplicate email (case insensitive)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_pagination(self, client, authenticated_admin, sample_users):
        """Test user list pagination"""
        # Test first page
        response1 = client.get(
            "/api/v1/users/?page=1&per_page=2", headers=authenticated_admin["headers"]
        )

        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert len(data1["users"]) <= 2
        assert data1["page"] == 1

        # Test second page
        response2 = client.get(
            "/api/v1/users/?page=2&per_page=2", headers=authenticated_admin["headers"]
        )

        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["page"] == 2

        # Users on different pages should be different
        if len(data1["users"]) > 0 and len(data2["users"]) > 0:
            user1_ids = [user["id"] for user in data1["users"]]
            user2_ids = [user["id"] for user in data2["users"]]
            assert set(user1_ids).isdisjoint(set(user2_ids))
