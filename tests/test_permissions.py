"""
Tests for Permission endpoints
"""

import pytest
import json
from fastapi import status

from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from tests.conftest import TEST_PERMISSION_DATA


class TestPermissionEndpoints:
    """Test class for Permission API endpoints"""

    def test_create_permission_success(self, client, authenticated_admin):
        """Test successful permission creation"""
        response = client.post(
            "/api/v1/permissions/",
            json=TEST_PERMISSION_DATA,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == TEST_PERMISSION_DATA["slug"]
        assert data["description"] == TEST_PERMISSION_DATA["description"]
        assert "id" in data
        assert "created_at" in data

    def test_create_permission_duplicate_slug(
        self, client, authenticated_admin, test_permission
    ):
        """Test creating permission with duplicate slug fails"""
        permission_data = {
            "slug": test_permission.slug,  # Same slug as existing permission
            "description": "Different description",
        }

        response = client.post(
            "/api/v1/permissions/",
            json=permission_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_create_permission_invalid_slug(self, client, authenticated_admin):
        """Test creating permission with invalid slug format fails"""
        invalid_data = {
            "slug": "Invalid Slug With Spaces!",  # Invalid characters
            "description": "Test description",
        }

        response = client.post(
            "/api/v1/permissions/",
            json=invalid_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_permissions_list(self, client, authenticated_user, sample_permissions):
        """Test getting list of permissions with pagination"""
        response = client.get(
            "/api/v1/permissions/?page=1&per_page=5",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "permissions" in data
        assert "total" in data
        assert "page" in data
        assert len(data["permissions"]) <= 5

    def test_get_permission_by_id_success(
        self, client, authenticated_user, test_permission
    ):
        """Test getting permission by ID"""
        response = client.get(
            f"/api/v1/permissions/{test_permission.id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_permission.id
        assert data["slug"] == test_permission.slug

    def test_get_permission_by_id_not_found(self, client, authenticated_user):
        """Test getting non-existent permission returns 404"""
        response = client.get(
            "/api/v1/permissions/999999", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_permission_success(
        self, client, authenticated_admin, test_permission
    ):
        """Test successful permission update"""
        update_data = {
            "slug": "updated-permission",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/permissions/{test_permission.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == update_data["slug"]
        assert data["description"] == update_data["description"]

    def test_update_permission_duplicate_slug(
        self, client, authenticated_admin, sample_permissions
    ):
        """Test updating permission with existing slug fails"""
        permission1, permission2 = sample_permissions[0], sample_permissions[1]

        update_data = {"slug": permission2.slug}  # Use existing slug

        response = client.put(
            f"/api/v1/permissions/{permission1.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_delete_permission_success(
        self, client, authenticated_admin, test_permission
    ):
        """Test successful permission deletion"""
        response = client.delete(
            f"/api/v1/permissions/{test_permission.id}",
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "deleted successfully" in response.json()["message"]

    def test_search_permissions(self, client, authenticated_user, sample_permissions):
        """Test permission search functionality"""
        response = client.get(
            "/api/v1/permissions/search?q=users&page=1&per_page=10",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "permissions" in data
        assert "search_term" in data
        assert data["search_term"] == "users"

    def test_assign_permissions_to_role_success(
        self, client, authenticated_admin, test_role, sample_permissions
    ):
        """Test successful permission assignment to role"""
        permission_slugs = [
            p.slug for p in sample_permissions[:3]
        ]  # First 3 permissions

        assign_data = {"permission_slugs": permission_slugs}

        response = client.post(
            f"/api/v1/permissions/roles/{test_role.id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role_id"] == test_role.id
        assert data["total_permissions"] == 3

    def test_assign_permissions_role_not_found(
        self, client, authenticated_admin, sample_permissions
    ):
        """Test permission assignment to non-existent role fails"""
        assign_data = {"permission_slugs": [sample_permissions[0].slug]}

        response = client.post(
            "/api/v1/permissions/roles/999999/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Role not found" in response.json()["detail"]

    def test_assign_permissions_invalid_slug(
        self, client, authenticated_admin, test_role
    ):
        """Test permission assignment with invalid slug fails"""
        assign_data = {"permission_slugs": ["non-existent-permission"]}

        response = client.post(
            f"/api/v1/permissions/roles/{test_role.id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Permissions not found" in response.json()["detail"]

    def test_unassign_permissions_from_role_success(
        self, client, authenticated_admin, test_role, sample_permissions, db_session
    ):
        """Test successful permission unassignment from role"""
        # First assign permissions to role
        for permission in sample_permissions[:2]:
            test_role.permissions.append(permission)
        db_session.commit()

        unassign_data = {"permission_slugs": [sample_permissions[0].slug]}

        response = client.post(
            f"/api/v1/permissions/roles/{test_role.id}/unassign",
            json=unassign_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_permissions"] == 1  # One permission left

    def test_get_role_permissions(
        self, client, authenticated_user, test_role, sample_permissions, db_session
    ):
        """Test getting permissions assigned to a role"""
        # Assign permissions to role
        for permission in sample_permissions[:3]:
            test_role.permissions.append(permission)
        db_session.commit()

        response = client.get(
            f"/api/v1/permissions/roles/{test_role.id}/permissions",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role_id"] == test_role.id
        assert data["total_permissions"] == 3

    def test_check_user_permission_success(
        self,
        client,
        authenticated_user,
        test_user,
        test_role,
        test_permission,
        db_session,
    ):
        """Test checking if user has specific permission"""
        # Assign permission to role, role to user
        test_role.permissions.append(test_permission)
        test_user.roles.append(test_role)
        db_session.commit()

        response = client.get(
            f"/api/v1/permissions/users/{test_user.id}/check/{test_permission.slug}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_permission"] is True
        assert test_role.name in data["granted_via_roles"]

    def test_check_user_permission_no_access(
        self, client, authenticated_user, test_user, test_permission
    ):
        """Test checking if user doesn't have specific permission"""
        response = client.get(
            f"/api/v1/permissions/users/{test_user.id}/check/{test_permission.slug}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_permission"] is False
        assert len(data["granted_via_roles"]) == 0

    def test_get_user_permissions(
        self,
        client,
        authenticated_user,
        test_user,
        test_role,
        sample_permissions,
        db_session,
    ):
        """Test getting all permissions for a user"""
        # Assign permissions to role, role to user
        for permission in sample_permissions[:3]:
            test_role.permissions.append(permission)
        test_user.roles.append(test_role)
        db_session.commit()

        response = client.get(
            f"/api/v1/permissions/users/{test_user.id}/permissions",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3  # Should return list of permissions

    def test_bulk_delete_permissions(
        self, client, authenticated_admin, sample_permissions
    ):
        """Test bulk deletion of permissions"""
        permission_ids = [p.id for p in sample_permissions[:3]]

        bulk_data = {"permission_ids": permission_ids}

        response = client.request(
            "DELETE",
            "/api/v1/permissions/bulk",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3
        assert data["failed_count"] == 0

    def test_bulk_delete_permissions_partial_fail(
        self, client, authenticated_admin, sample_permissions
    ):
        """Test bulk deletion with some non-existent permissions"""
        valid_ids = [sample_permissions[0].id, sample_permissions[1].id]
        invalid_ids = [999999, 888888]
        all_ids = valid_ids + invalid_ids

        bulk_data = {"permission_ids": all_ids}

        response = client.request(
            "DELETE",
            "/api/v1/permissions/bulk",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 2
        assert data["failed_count"] == 2

    def test_permission_unauthorized_access(self, client, authenticated_user):
        """Test that non-admin users cannot create/update/delete permissions"""
        # Test create
        response = client.post(
            "/api/v1/permissions/",
            json=TEST_PERMISSION_DATA,
            headers=authenticated_user["headers"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test update
        response = client.put(
            "/api/v1/permissions/1",
            json={"description": "Updated"},
            headers=authenticated_user["headers"],
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test delete
        response = client.delete(
            "/api/v1/permissions/1", headers=authenticated_user["headers"]
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_permission_slug_validation(self, client, authenticated_admin):
        """Test permission slug validation rules"""
        # Test with uppercase (should be rejected)
        invalid_data = {"slug": "UPPERCASE-SLUG", "description": "Test"}
        response = client.post(
            "/api/v1/permissions/",
            json=invalid_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test with spaces (should be rejected)
        invalid_data = {"slug": "slug with spaces", "description": "Test"}
        response = client.post(
            "/api/v1/permissions/",
            json=invalid_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test with valid slug (should succeed)
        valid_data = {"slug": "valid-slug_123", "description": "Test"}
        response = client.post(
            "/api/v1/permissions/",
            json=valid_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK
