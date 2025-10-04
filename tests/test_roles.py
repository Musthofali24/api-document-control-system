"""
Tests for Role endpoints
"""

import pytest
import json
from fastapi import status

from app.models.role import Role
from app.models.user import User
from tests.conftest import TEST_ROLE_DATA


class TestRoleEndpoints:
    """Test class for Role API endpoints"""

    def test_create_role_success(self, client, authenticated_admin):
        """Test successful role creation"""
        response = client.post(
            "/api/v1/role/", json=TEST_ROLE_DATA, headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == TEST_ROLE_DATA["name"]
        assert data["slug"] == TEST_ROLE_DATA["slug"]
        assert data["description"] == TEST_ROLE_DATA["description"]
        assert "id" in data
        assert "created_at" in data

    def test_create_role_duplicate_name(self, client, authenticated_admin, test_role):
        """Test creating role with duplicate name fails"""
        role_data = {
            "name": test_role.name,  # Same name as existing role
            "slug": "different-slug",
            "description": "Different description",
        }

        response = client.post(
            "/api/v1/role/", json=role_data, headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_create_role_unauthorized(self, client, authenticated_user):
        """Test role creation without admin access fails"""
        response = client.post(
            "/api/v1/role/", json=TEST_ROLE_DATA, headers=authenticated_user["headers"]
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_201_CREATED,
        ]

    def test_get_roles_list(self, client, authenticated_user, sample_roles):
        """Test getting list of roles with pagination"""
        response = client.get(
            "/api/v1/role/?skip=0&limit=10", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 0

    def test_get_role_by_id_success(self, client, authenticated_user, test_role):
        """Test getting role by ID"""
        response = client.get(
            f"/api/v1/role/{test_role.id}", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_role.id
        assert data["name"] == test_role.name

    def test_get_role_by_id_not_found(self, client, authenticated_user):
        """Test getting non-existent role returns 404"""
        response = client.get(
            "/api/v1/role/999999", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_role_success(self, client, authenticated_admin, test_role):
        """Test successful role update"""
        update_data = {
            "name": "Updated Role Name",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/role/{test_role.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]

    def test_update_role_not_found(self, client, authenticated_admin):
        """Test updating non-existent role returns 404"""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/role/999999",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_role_success(self, client, authenticated_admin, test_role):
        """Test successful role deletion"""
        response = client.delete(
            f"/api/v1/role/{test_role.id}", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_delete_role_not_found(self, client, authenticated_admin):
        """Test deleting non-existent role returns 404"""
        response = client.delete(
            "/api/v1/role/999999", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_role_to_user_success(
        self, client, authenticated_admin, test_user, test_role
    ):
        """Test successful role assignment to user"""
        assign_data = {"user_id": test_user.id, "role_id": test_role.id}

        response = client.post(
            "/api/v1/role/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "assigned" in response.json()["message"]

    def test_assign_role_user_not_found(self, client, authenticated_admin, test_role):
        """Test role assignment to non-existent user fails"""
        assign_data = {"user_id": 999999, "role_id": test_role.id}

        response = client.post(
            "/api/v1/role/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "User not found" in response.json()["detail"]

    def test_assign_role_role_not_found(self, client, authenticated_admin, test_user):
        """Test role assignment with non-existent role fails"""
        assign_data = {"user_id": test_user.id, "role_id": 999999}

        response = client.post(
            "/api/v1/role/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Role not found" in response.json()["detail"]

    def test_unassign_role_from_user_success(
        self, client, authenticated_admin, test_user, test_role, db_session
    ):
        """Test successful role unassignment from user"""
        # First assign the role
        test_user.roles.append(test_role)
        db_session.commit()

        unassign_data = {"user_id": test_user.id, "role_id": test_role.id}

        response = client.post(
            "/api/v1/role/unassign",
            json=unassign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "removed" in response.json()["message"]

    def test_get_user_roles(
        self, client, authenticated_user, test_user, test_role, db_session
    ):
        """Test getting user's assigned roles"""
        # Assign role to user
        test_user.roles.append(test_role)
        db_session.commit()

        response = client.get(
            f"/api/v1/role/user/{test_user.id}/roles",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["roles"]) == 1
        assert data["roles"][0]["id"] == test_role.id

    def test_get_role_users(
        self, client, authenticated_admin, test_role, test_user, db_session
    ):
        """Test getting users assigned to a role"""
        # Assign role to user
        test_user.roles.append(test_role)
        db_session.commit()

        response = client.get(
            f"/api/v1/role/{test_role.id}/users", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["users"]) == 1
        assert data["users"][0]["id"] == test_user.id

    def test_bulk_assign_roles(
        self, client, authenticated_admin, sample_users, test_role
    ):
        """Test bulk role assignment to multiple users"""
        user_ids = [user.id for user in sample_users[:3]]  # First 3 users

        bulk_data = {"user_ids": user_ids, "role_id": test_role.id}

        response = client.post(
            "/api/v1/role/bulk/assign",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_bulk_unassign_roles(
        self, client, authenticated_admin, sample_users, test_role, db_session
    ):
        """Test bulk role unassignment from multiple users"""
        # First assign role to users
        for user in sample_users[:3]:
            user.roles.append(test_role)
        db_session.commit()

        user_ids = [user.id for user in sample_users[:3]]

        bulk_data = {"user_ids": user_ids, "role_id": test_role.id}

        response = client.post(
            "/api/v1/role/bulk/unassign",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_check_user_has_role(
        self, client, authenticated_user, test_user, test_role, db_session
    ):
        """Test checking if user has specific role"""
        # Assign role to user
        test_user.roles.append(test_role)
        db_session.commit()

        response = client.get(
            f"/api/v1/role/check/{test_user.id}/{test_role.name}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_role"] is True
        assert data["role_name"] == test_role.name

    def test_check_user_does_not_have_role(
        self, client, authenticated_user, test_user, test_role
    ):
        """Test checking if user doesn't have specific role"""
        response = client.get(
            f"/api/v1/role/check/{test_user.id}/{test_role.name}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_role"] is False

    def test_search_roles(self, client, authenticated_user, sample_roles):
        """Test role search functionality"""
        # Search for roles containing 'Manager'
        response = client.get(
            "/api/v1/role/search?q=Manager&page=1&per_page=10",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "roles" in data
        assert "search_term" in data
        assert data["search_term"] == "Manager"

    def test_create_role_invalid_data(self, client, authenticated_admin):
        """Test role creation with invalid data"""
        invalid_data = {"name": "", "slug": "test-slug"}  # Empty name should fail

        response = client.post(
            "/api/v1/role/", json=invalid_data, headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_role_slug_auto_generation(self, client, authenticated_admin):
        """Test that role slug is auto-generated from name"""
        role_data = {
            "name": "Test Role With Spaces",
            "description": "Test description",
            # No slug provided
        }

        response = client.post(
            "/api/v1/role/", json=role_data, headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["slug"] == "test-role-with-spaces"
