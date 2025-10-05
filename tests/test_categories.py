"""
Comprehensive test suite for Category management endpoints
"""

import pytest
from fastapi import status

from app.models.category import Category


class TestCategoryEndpoints:
    """Test Category CRUD operations"""

    def test_create_category_success(self, client, authenticated_admin):
        """Test successful category creation"""
        category_data = {
            "name": "Test Category",
        }

        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == category_data["name"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_category_duplicate_slug(
        self, client, authenticated_admin, sample_categories
    ):
        """Test creating category with duplicate slug"""
        category_data = {
            "name": "Duplicate Category",
            "slug": sample_categories[0].slug,  # Use existing slug
            "description": "This should fail",
        }

        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_category_missing_fields(self, client, authenticated_admin):
        """Test category creation with missing required fields"""
        category_data = {"description": "Missing name and slug"}

        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_category_unauthorized(self, client, authenticated_user):
        """Test category creation without admin permissions"""
        category_data = {
            "name": "Unauthorized Category",
            "slug": "unauthorized-category",
            "description": "Should fail",
        }

        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=authenticated_user["headers"],
        )

        # Should fail if user doesn't have admin permissions
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_category_success(self, client, authenticated_user, sample_categories):
        """Test successful category retrieval"""
        category = sample_categories[0]

        response = client.get(
            f"/api/v1/categories/{category.id}", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == category.id
        assert data["name"] == category.name
        assert data["slug"] == category.slug

    def test_get_category_by_slug(self, client, authenticated_user, sample_categories):
        """Test getting category by slug"""
        category = sample_categories[0]

        response = client.get(
            f"/api/v1/categories/slug/{category.slug}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == category.id
        assert data["slug"] == category.slug

    def test_get_category_not_found(self, client, authenticated_user):
        """Test getting non-existent category"""
        response = client.get(
            "/api/v1/categories/999999", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_categories_list(self, client, authenticated_user, sample_categories):
        """Test getting paginated list of categories"""
        response = client.get(
            "/api/v1/categories/?page=1&size=10", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) <= 10

    def test_get_categories_active_only(
        self, client, authenticated_user, sample_categories
    ):
        """Test getting only active categories"""
        response = client.get(
            "/api/v1/categories/?active_only=true",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["is_active"] is True

    def test_get_categories_with_search(
        self, client, authenticated_user, sample_categories
    ):
        """Test getting categories with search filter"""
        search_term = sample_categories[0].name[:3]

        response = client.get(
            f"/api/v1/categories/?search={search_term}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) >= 1

    def test_update_category_success(
        self, client, db_session, authenticated_admin, sample_categories
    ):
        """Test successful category update"""
        category = sample_categories[0]
        update_data = {
            "name": "Updated Category Name",
            "description": "Updated description",
        }

        response = client.put(
            f"/api/v1/categories/{category.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["slug"] == category.slug  # Slug should not change

    def test_update_category_slug(self, client, authenticated_admin, sample_categories):
        """Test updating category slug"""
        category = sample_categories[0]
        update_data = {"slug": "new-updated-slug"}

        response = client.put(
            f"/api/v1/categories/{category.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == update_data["slug"]

    def test_update_category_duplicate_slug(
        self, client, authenticated_admin, sample_categories
    ):
        """Test updating category with duplicate slug"""
        category1, category2 = sample_categories[0], sample_categories[1]
        update_data = {"slug": category2.slug}  # Try to use another category's slug

        response = client.put(
            f"/api/v1/categories/{category1.id}",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_category_unauthorized(
        self, client, authenticated_user, sample_categories
    ):
        """Test updating category without admin permissions"""
        category = sample_categories[0]
        update_data = {"name": "Unauthorized Update"}

        response = client.put(
            f"/api/v1/categories/{category.id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_update_category_not_found(self, client, authenticated_admin):
        """Test updating non-existent category"""
        update_data = {"name": "Updated Name"}

        response = client.put(
            "/api/v1/categories/999999",
            json=update_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category_success(
        self, client, db_session, authenticated_admin, sample_categories
    ):
        """Test successful category deletion"""
        # Use the last category to avoid FK constraints
        category = sample_categories[-1]
        category_id = category.id

        response = client.delete(
            f"/api/v1/categories/{category_id}", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify category is deleted
        get_response = client.get(
            f"/api/v1/categories/{category_id}", headers=authenticated_admin["headers"]
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_category_with_documents(
        self, client, authenticated_admin, sample_categories, sample_documents
    ):
        """Test deleting category that has associated documents"""
        # Find category that has documents
        category_with_docs = None
        for category in sample_categories:
            if any(doc.category_id == category.id for doc in sample_documents):
                category_with_docs = category
                break

        if category_with_docs:
            response = client.delete(
                f"/api/v1/categories/{category_with_docs.id}",
                headers=authenticated_admin["headers"],
            )

            # Should fail due to foreign key constraint or return specific error
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_409_CONFLICT,
            ]

    def test_delete_category_unauthorized(
        self, client, authenticated_user, sample_categories
    ):
        """Test deleting category without admin permissions"""
        category = sample_categories[0]

        response = client.delete(
            f"/api/v1/categories/{category.id}", headers=authenticated_user["headers"]
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_delete_category_not_found(self, client, authenticated_admin):
        """Test deleting non-existent category"""
        response = client.delete(
            "/api/v1/categories/999999", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_toggle_category_status(
        self, client, db_session, authenticated_admin, sample_categories
    ):
        """Test toggling category active status"""
        category = sample_categories[0]
        original_status = category.is_active

        response = client.put(
            f"/api/v1/categories/{category.id}/toggle-status",
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] != original_status

    def test_category_statistics(
        self, client, authenticated_admin, sample_categories, sample_documents
    ):
        """Test getting category statistics"""
        response = client.get(
            "/api/v1/categories/statistics", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_categories" in data
        assert "active_categories" in data
        assert "categories_with_documents" in data
        assert "document_count_by_category" in data

    def test_category_documents_count(
        self, client, authenticated_user, sample_categories, sample_documents
    ):
        """Test getting document count for each category"""
        response = client.get(
            "/api/v1/categories/with-document-counts",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        for item in data["items"]:
            assert "document_count" in item
            assert isinstance(item["document_count"], int)

    def test_category_tree_structure(self, client, authenticated_user):
        """Test getting category tree structure (if hierarchical)"""
        response = client.get(
            "/api/v1/categories/tree", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        # Structure depends on whether categories support hierarchy

    def test_bulk_category_operations(
        self, client, authenticated_admin, sample_categories
    ):
        """Test bulk category operations"""
        category_ids = [cat.id for cat in sample_categories[:2]]

        # Bulk status change
        bulk_data = {"category_ids": category_ids, "is_active": False}

        response = client.put(
            "/api/v1/categories/bulk/status",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 2

    def test_bulk_category_delete(self, client, authenticated_admin):
        """Test bulk category deletion"""
        # Create temporary categories for deletion
        categories_to_delete = []
        for i in range(3):
            cat_data = {
                "name": f"Temp Category {i}",
                "slug": f"temp-cat-{i}",
                "description": "Temporary category",
            }
            response = client.post(
                "/api/v1/categories/",
                json=cat_data,
                headers=authenticated_admin["headers"],
            )
            categories_to_delete.append(response.json()["id"])

        # Bulk delete
        bulk_data = {"category_ids": categories_to_delete}

        response = client.delete(
            "/api/v1/categories/bulk/delete",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted_count"] == 3

    def test_category_export(self, client, authenticated_admin, sample_categories):
        """Test exporting categories to CSV/Excel"""
        response = client.get(
            "/api/v1/categories/export?format=csv",
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/csv" in response.headers.get("content-type", "")

    def test_category_import(self, client, authenticated_admin):
        """Test importing categories from file"""
        import io

        # Create CSV content
        csv_content = """name,slug,description
Import Category 1,import-cat-1,First imported category
Import Category 2,import-cat-2,Second imported category"""

        files = {"file": ("categories.csv", io.StringIO(csv_content), "text/csv")}

        response = client.post(
            "/api/v1/categories/import",
            files=files,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["imported_count"] >= 0

    def test_category_validation_errors(self, client, authenticated_admin):
        """Test various category validation scenarios"""
        # Test name too long
        invalid_data = {
            "name": "A" * 101,  # Assuming 100 char limit
            "slug": "valid-slug",
            "description": "Valid description",
        }

        response = client.post(
            "/api/v1/categories/",
            json=invalid_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid slug format (special characters)
        invalid_slug_data = {
            "name": "Valid Name",
            "slug": "invalid slug with spaces!",
            "description": "Valid description",
        }

        response = client.post(
            "/api/v1/categories/",
            json=invalid_slug_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_category_search_advanced(
        self, client, authenticated_user, sample_categories
    ):
        """Test advanced category search functionality"""
        # Search by description
        response = client.get(
            "/api/v1/categories/search?query=description&search_in=description",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

        # Search with sorting
        response = client.get(
            "/api/v1/categories/search?sort_by=name&sort_order=desc",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

    def test_category_recent_activity(
        self, client, authenticated_admin, sample_categories
    ):
        """Test getting recent category activity"""
        response = client.get(
            "/api/v1/categories/recent-activity", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_category_unauthorized_access(self, client, sample_categories):
        """Test accessing categories without authentication"""
        response = client.get(f"/api/v1/categories/{sample_categories[0].id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_category_slug_generation(self, client, authenticated_admin):
        """Test automatic slug generation from name"""
        category_data = {
            "name": "Auto Slug Category Test",
            "description": "Testing automatic slug generation",
            # No slug provided
        }

        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["slug"] == "auto-slug-category-test"  # Auto-generated slug

    def test_category_document_association(
        self, client, authenticated_user, sample_categories
    ):
        """Test getting documents associated with a category"""
        category = sample_categories[0]

        response = client.get(
            f"/api/v1/categories/{category.id}/documents",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        # All documents should belong to this category
        for doc in data["items"]:
            assert doc["category_id"] == category.id

    def test_category_move_documents(
        self, client, authenticated_admin, sample_categories, sample_documents
    ):
        """Test moving documents from one category to another"""
        source_category = sample_categories[0]
        target_category = sample_categories[1]

        # Find documents in source category
        doc_ids = [
            doc.id for doc in sample_documents if doc.category_id == source_category.id
        ]

        if doc_ids:
            move_data = {
                "document_ids": doc_ids[:2],  # Move first 2 documents
                "target_category_id": target_category.id,
            }

            response = client.put(
                f"/api/v1/categories/{source_category.id}/move-documents",
                json=move_data,
                headers=authenticated_admin["headers"],
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["moved_count"] >= 0
