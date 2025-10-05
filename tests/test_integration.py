"""
Integration tests for the complete RBAC (Role-Based Access Control) system
"""

import pytest
from fastapi import status

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission


class TestRBACIntegration:
    """Integration tests for Role-Based Access Control system"""

    def test_complete_rbac_flow(self, client, db_session, authenticated_admin):
        """Test complete RBAC flow: create role -> create permission -> assign -> check access"""

        # Step 1: Create a role
        role_data = {
            "name": "Document Manager",
            "slug": "document-manager",
            "description": "Can manage documents",
        }

        role_response = client.post(
            "/api/v1/role/", json=role_data, headers=authenticated_admin["headers"]
        )
        assert role_response.status_code == status.HTTP_201_CREATED
        role_id = role_response.json()["id"]

        # Step 2: Create permissions
        permission_data = [
            {"slug": "documents.create", "description": "Create documents"},
            {"slug": "documents.update", "description": "Update documents"},
            {"slug": "documents.delete", "description": "Delete documents"},
        ]

        permission_ids = []
        for perm_data in permission_data:
            perm_response = client.post(
                "/api/v1/permissions/", json=perm_data, headers=authenticated_admin["headers"]
            )
            assert perm_response.status_code == status.HTTP_201_CREATED
            permission_ids.append(perm_response.json()["id"])

        # Step 3: Assign permissions to role
        assign_data = {"permission_slugs": [perm["slug"] for perm in permission_data]}

        assign_response = client.post(
            f"/api/v1/permissions/roles/{role_id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )
        assert assign_response.status_code == status.HTTP_200_OK
        assert assign_response.json()["total_permissions"] == 3

        # Step 4: Create a test user
        user_data = {
            "name": "Test Document Manager",
            "email": "docmanager@example.com",
            "password": "password123",
        }

        user_response = client.post(
            "/api/v1/users/", json=user_data, headers=authenticated_admin["headers"]
        )
        assert user_response.status_code == status.HTTP_200_OK
        user_id = user_response.json()["id"]

        # Step 5: Assign role to user
        role_assign_data = {"user_id": user_id, "role_id": role_id}

        role_assign_response = client.post(
            "/api/v1/role/assign",
            json=role_assign_data,
            headers=authenticated_admin["headers"],
        )
        assert role_assign_response.status_code == status.HTTP_200_OK

        # Step 6: Check user permissions
        for perm_data in permission_data:
            perm_check_response = client.get(
                f"/api/v1/permissions/users/{user_id}/check/{perm_data['slug']}",
                headers=authenticated_admin["headers"],
            )
            assert perm_check_response.status_code == status.HTTP_200_OK
            assert perm_check_response.json()["has_permission"] is True

    def test_hierarchical_permissions(
        self, client, db_session, authenticated_admin, sample_users
    ):
        """Test hierarchical permission system with multiple roles"""

        # Create roles with different permission levels
        roles_data = [
            {"name": "Viewer", "slug": "viewer", "description": "Read-only access"},
            {"name": "Editor", "slug": "editor", "description": "Can edit content"},
            {"name": "Admin", "slug": "admin", "description": "Full access"},
        ]

        created_roles = []
        for role_data in roles_data:
            response = client.post(
                "/api/v1/role/", json=role_data, headers=authenticated_admin["headers"]
            )
            assert response.status_code == status.HTTP_200_OK
            created_roles.append(response.json())

        # Create hierarchical permissions
        permissions_hierarchy = {
            "viewer": ["documents.read", "categories.read"],
            "editor": [
                "documents.read",
                "documents.create",
                "documents.update",
                "categories.read",
            ],
            "admin": [
                "documents.read",
                "documents.create",
                "documents.update",
                "documents.delete",
                "categories.read",
                "categories.create",
                "categories.update",
                "categories.delete",
                "users.manage",
                "roles.manage",
            ],
        }

        # Create all permissions
        all_permissions = set()
        for perms in permissions_hierarchy.values():
            all_permissions.update(perms)

        created_permissions = {}
        for perm_slug in all_permissions:
            perm_data = {"slug": perm_slug, "description": f"Permission to {perm_slug}"}
            response = client.post(
                "/api/v1/permissions/", json=perm_data, headers=authenticated_admin["headers"]
            )
            assert response.status_code == status.HTTP_200_OK
            created_permissions[perm_slug] = response.json()

        # Assign permissions to roles
        for i, role in enumerate(created_roles):
            role_slug = roles_data[i]["slug"]
            perms_for_role = permissions_hierarchy[role_slug]

            assign_data = {"permission_slugs": perms_for_role}
            response = client.post(
                f"/api/v1/permissions/roles/{role['id']}/assign",
                json=assign_data,
                headers=authenticated_admin["headers"],
            )
            assert response.status_code == status.HTTP_200_OK

        # Assign roles to users
        for i, user in enumerate(sample_users[:3]):
            role = created_roles[i]
            assign_data = {"user_id": user.id, "role_id": role["id"]}

            response = client.post(
                "/api/v1/role/assign", json=assign_data, headers=authenticated_admin["headers"]
            )
            assert response.status_code == status.HTTP_200_OK

        # Verify permission inheritance
        # Viewer should only have read permissions
        viewer_perms = client.get(
            f"/api/v1/permissions/users/{sample_users[0].id}/permissions",
            headers=authenticated_admin["headers"],
        ).json()
        viewer_perm_slugs = [p["slug"] for p in viewer_perms]
        assert "documents.read" in viewer_perm_slugs
        assert "documents.delete" not in viewer_perm_slugs

        # Admin should have all permissions
        admin_perms = client.get(
            f"/api/v1/permissions/users/{sample_users[2].id}/permissions",
            headers=authenticated_admin["headers"],
        ).json()
        admin_perm_slugs = [p["slug"] for p in admin_perms]
        assert "documents.delete" in admin_perm_slugs
        assert "users.manage" in admin_perm_slugs

    def test_multiple_roles_per_user(
        self,
        client,
        db_session,
        authenticated_admin,
        test_user,
        sample_roles,
        sample_permissions,
    ):
        """Test user with multiple roles and combined permissions"""

        # Assign different permissions to different roles
        role1, role2 = sample_roles[0], sample_roles[1]
        perm1, perm2, perm3 = (
            sample_permissions[0],
            sample_permissions[1],
            sample_permissions[2],
        )

        # Role 1 gets permissions 1 and 2
        assign_data1 = {"permission_slugs": [perm1.slug, perm2.slug]}
        response = client.post(
            f"/api/v1/permissions/roles/{role1.id}/assign",
            json=assign_data1,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Role 2 gets permissions 2 and 3 (permission 2 overlaps)
        assign_data2 = {"permission_slugs": [perm2.slug, perm3.slug]}
        response = client.post(
            f"/api/v1/permissions/roles/{role2.id}/assign",
            json=assign_data2,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Assign both roles to user
        for role in [role1, role2]:
            assign_data = {"user_id": test_user.id, "role_id": role.id}
            response = client.post(
                "/api/v1/role/assign", json=assign_data, headers=authenticated_admin["headers"]
            )
            assert response.status_code == status.HTTP_200_OK

        # User should have all three permissions (union of both roles)
        user_perms = client.get(
            f"/api/v1/permissions/users/{test_user.id}/permissions",
            headers=authenticated_admin["headers"],
        ).json()

        user_perm_slugs = [p["slug"] for p in user_perms]
        assert perm1.slug in user_perm_slugs
        assert perm2.slug in user_perm_slugs
        assert perm3.slug in user_perm_slugs

    def test_permission_revocation_cascade(
        self,
        client,
        db_session,
        authenticated_admin,
        test_user,
        test_role,
        sample_permissions,
    ):
        """Test that removing permissions from role affects user access"""

        # Setup: assign permissions to role, role to user
        permissions_to_assign = sample_permissions[:3]
        assign_data = {"permission_slugs": [p.slug for p in permissions_to_assign]}

        # Assign permissions to role
        response = client.post(
            f"/api/v1/permissions/roles/{test_role.id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Assign role to user
        role_assign_data = {"user_id": test_user.id, "role_id": test_role.id}
        response = client.post(
            "/api/v1/role/assign",
            json=role_assign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify user has all permissions
        for perm in permissions_to_assign:
            response = client.get(
                f"/api/v1/permissions/users/{test_user.id}/check/{perm.slug}",
                headers=authenticated_admin["headers"],
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["has_permission"] is True

        # Remove one permission from role
        unassign_data = {"permission_slugs": [permissions_to_assign[0].slug]}
        response = client.post(
            f"/api/v1/permissions/roles/{test_role.id}/unassign",
            json=unassign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify user no longer has that permission
        response = client.get(
            f"/api/v1/permissions/users/{test_user.id}/check/{permissions_to_assign[0].slug}",
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["has_permission"] is False

        # But still has the other permissions
        for perm in permissions_to_assign[1:]:
            response = client.get(
                f"/api/v1/permissions/users/{test_user.id}/check/{perm.slug}",
                headers=authenticated_admin["headers"],
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["has_permission"] is True

    def test_role_deletion_effects(
        self, client, db_session, authenticated_admin, sample_users, sample_permissions
    ):
        """Test effects of deleting a role on users and permissions"""

        # Create a test role
        role_data = {
            "name": "Temporary Role",
            "slug": "temp-role",
            "description": "Will be deleted",
        }
        role_response = client.post(
            "/api/v1/role/", json=role_data, headers=authenticated_admin["headers"]
        )
        assert role_response.status_code == status.HTTP_201_CREATED
        role_id = role_response.json()["id"]

        # Assign permissions to role
        assign_data = {"permission_slugs": [p.slug for p in sample_permissions[:2]]}
        response = client.post(
            f"/api/v1/permissions/roles/{role_id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Assign role to users
        for user in sample_users[:2]:
            role_assign_data = {"user_id": user.id, "role_id": role_id}
            response = client.post(
                "/api/v1/role/assign",
                json=role_assign_data,
                headers=authenticated_admin["headers"],
            )
            assert response.status_code == status.HTTP_200_OK

        # Verify users have permissions
        for user in sample_users[:2]:
            for perm in sample_permissions[:2]:
                response = client.get(
                    f"/api/v1/permissions/users/{user.id}/check/{perm.slug}",
                    headers=authenticated_admin["headers"],
                )
                assert response.status_code == status.HTTP_200_OK
                assert response.json()["has_permission"] is True

        # Delete the role
        response = client.delete(
            f"/api/v1/role/{role_id}", headers=authenticated_admin["headers"]
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify users no longer have those permissions
        for user in sample_users[:2]:
            for perm in sample_permissions[:2]:
                response = client.get(
                    f"/api/v1/permissions/users/{user.id}/check/{perm.slug}",
                    headers=authenticated_admin["headers"],
                )
                assert response.status_code == status.HTTP_200_OK
                assert response.json()["has_permission"] is False

    def test_bulk_role_operations(
        self, client, db_session, authenticated_admin, sample_users, test_role
    ):
        """Test bulk role assignment and unassignment"""

        # Bulk assign role to multiple users
        user_ids = [user.id for user in sample_users[:3]]
        bulk_assign_data = {"user_ids": user_ids, "role_id": test_role.id}

        response = client.post(
            "/api/v1/role/bulk/assign",
            json=bulk_assign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 3

        # Verify all users have the role
        for user in sample_users[:3]:
            response = client.get(
                f"/api/v1/role/check/{user.id}/{test_role.name}",
                headers=authenticated_admin["headers"],
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["has_role"] is True

        # Bulk unassign role from users
        bulk_unassign_data = {
            "user_ids": user_ids[:2],
            "role_id": test_role.id,
        }  # Only first 2 users

        response = client.post(
            "/api/v1/role/bulk/unassign",
            json=bulk_unassign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_count"] == 2

        # Verify first 2 users no longer have the role
        for user in sample_users[:2]:
            response = client.get(
                f"/api/v1/role/check/{user.id}/{test_role.name}",
                headers=authenticated_admin["headers"],
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["has_role"] is False

        # Third user should still have the role
        response = client.get(
            f"/api/v1/role/check/{sample_users[2].id}/{test_role.name}",
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["has_role"] is True

    def test_permission_inheritance_through_notification_system(
        self,
        client,
        db_session,
        authenticated_admin,
        test_user,
        admin_role,
        admin_permission,
    ):
        """Test RBAC integration with notification system"""

        # Setup admin user with admin role and permission
        admin_user = authenticated_admin["user"]
        admin_user.roles.append(admin_role)
        admin_role.permissions.append(admin_permission)
        db_session.commit()

        # Admin should be able to send notifications
        notification_data = {
            "user_id": test_user.id,
            "type": "admin_message",
            "title": "Admin Message",
            "message": "This is from admin",
        }

        response = client.post(
            "/api/v1/notifications/send",
            json=notification_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Regular user should not be able to send notifications to others
        # (This test assumes permission checking is implemented in notification endpoints)
        user_token = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpass123",  # This assumes test_user password
            },
        )

        if user_token.status_code == status.HTTP_200_OK:
            user_headers = {
                "Authorization": f"Bearer {user_token.json()['access_token']}"
            }

            response = client.post(
                "/api/v1/notifications/send", json=notification_data, headers=user_headers
            )
            # Should fail due to lack of permissions
            assert response.status_code in [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ]

    def test_cross_system_permission_validation(
        self, client, db_session, authenticated_admin, sample_users, sample_permissions
    ):
        """Test permission validation across different system components"""

        # Create roles for different system areas
        document_role_data = {
            "name": "Document Admin",
            "slug": "doc-admin",
            "description": "Document management",
        }
        user_role_data = {
            "name": "User Admin",
            "slug": "user-admin",
            "description": "User management",
        }

        doc_role_response = client.post(
            "/api/v1/role/", json=document_role_data, headers=authenticated_admin["headers"]
        )
        user_role_response = client.post(
            "/api/v1/role/", json=user_role_data, headers=authenticated_admin["headers"]
        )

        assert doc_role_response.status_code == status.HTTP_200_OK
        assert user_role_response.status_code == status.HTTP_200_OK

        doc_role_id = doc_role_response.json()["id"]
        user_role_id = user_role_response.json()["id"]

        # Create system-specific permissions
        doc_permissions = ["documents.create", "documents.delete"]
        user_permissions = ["users.create", "users.delete"]

        # Create and assign document permissions
        for perm_slug in doc_permissions:
            perm_data = {
                "slug": perm_slug,
                "description": f"Permission for {perm_slug}",
            }
            perm_response = client.post(
                "/api/v1/permissions/", json=perm_data, headers=authenticated_admin["headers"]
            )
            assert perm_response.status_code == status.HTTP_201_CREATED

        assign_data = {"permission_slugs": doc_permissions}
        response = client.post(
            f"/api/v1/permissions/roles/{doc_role_id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Create and assign user permissions
        for perm_slug in user_permissions:
            perm_data = {
                "slug": perm_slug,
                "description": f"Permission for {perm_slug}",
            }
            perm_response = client.post(
                "/api/v1/permissions/", json=perm_data, headers=authenticated_admin["headers"]
            )
            assert perm_response.status_code == status.HTTP_201_CREATED

        assign_data = {"permission_slugs": user_permissions}
        response = client.post(
            f"/api/v1/permissions/roles/{user_role_id}/assign",
            json=assign_data,
            headers=authenticated_admin["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Assign roles to users
        doc_admin_assign = {"user_id": sample_users[0].id, "role_id": doc_role_id}
        user_admin_assign = {"user_id": sample_users[1].id, "role_id": user_role_id}

        client.post(
            "/api/v1/role/assign",
            json=doc_admin_assign,
            headers=authenticated_admin["headers"],
        )
        client.post(
            "/api/v1/role/assign",
            json=user_admin_assign,
            headers=authenticated_admin["headers"],
        )

        # Verify cross-system permission boundaries
        # Document admin should have document permissions but not user permissions
        doc_check = client.get(
            f"/api/v1/permissions/users/{sample_users[0].id}/check/documents.create",
            headers=authenticated_admin["headers"],
        )
        assert doc_check.json()["has_permission"] is True

        user_check = client.get(
            f"/api/v1/permissions/users/{sample_users[0].id}/check/users.create",
            headers=authenticated_admin["headers"],
        )
        assert user_check.json()["has_permission"] is False

        # User admin should have user permissions but not document permissions
        user_check = client.get(
            f"/api/v1/permissions/users/{sample_users[1].id}/check/users.create",
            headers=authenticated_admin["headers"],
        )
        assert user_check.json()["has_permission"] is True

        doc_check = client.get(
            f"/api/v1/permissions/users/{sample_users[1].id}/check/documents.create",
            headers=authenticated_admin["headers"],
        )
        assert doc_check.json()["has_permission"] is False
