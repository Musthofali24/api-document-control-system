"""
Comprehensive test suite for Document management endpoints
"""

import pytest
from datetime import datetime, timedelta
import io
from unittest.mock import patch
from fastapi import status, UploadFile

from app.models.document import (
    Document,
    DocumentRevision,
    DocumentStatus,
    RevisionStatus,
)
from app.models.category import Category
from app.models.user import User


class TestDocumentEndpoints:
    """Test Document CRUD and management operations"""

    def test_create_document_success(
        self, client, db_session, authenticated_user, sample_categories
    ):
        """Test successful document creation"""
        document_data = {
            "title": "Test Document",
            "description": "A test document for validation",
            "category_id": sample_categories[0].id,
            "content": "This is the content of the test document",
        }

        response = client.post(
            "/documents/", json=document_data, headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == document_data["title"]
        assert data["description"] == document_data["description"]
        assert data["category_id"] == document_data["category_id"]
        assert data["status"] == DocumentStatus.DRAFT.value
        assert data["version"] == "1.0"
        assert data["created_by"] == authenticated_user["user"].id

    def test_create_document_invalid_category(self, client, authenticated_user):
        """Test document creation with invalid category"""
        document_data = {
            "title": "Test Document",
            "description": "A test document",
            "category_id": 999999,  # Non-existent category
            "content": "Test content",
        }

        response = client.post(
            "/documents/", json=document_data, headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_document_missing_fields(self, client, authenticated_user):
        """Test document creation with missing required fields"""
        document_data = {"description": "Missing title"}

        response = client.post(
            "/documents/", json=document_data, headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_document_success(self, client, authenticated_user, sample_document):
        """Test successful document retrieval"""
        response = client.get(
            f"/documents/{sample_document.id}", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_document.id
        assert data["title"] == sample_document.title
        assert "category" in data
        assert "created_by_user" in data

    def test_get_document_not_found(self, client, authenticated_user):
        """Test getting non-existent document"""
        response = client.get(
            "/documents/999999", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_documents_list(self, client, authenticated_user, sample_documents):
        """Test getting paginated list of documents"""
        response = client.get(
            "/documents/?page=1&size=10", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) <= 10

    def test_get_documents_with_filters(
        self, client, authenticated_user, sample_documents
    ):
        """Test getting documents with search and status filters"""
        # Test search by title
        response = client.get(
            f"/documents/?search={sample_documents[0].title[:5]}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) >= 1

        # Test filter by status
        response = client.get(
            "/documents/?status=draft", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["status"] == DocumentStatus.DRAFT.value

    def test_get_documents_by_category(
        self, client, authenticated_user, sample_documents
    ):
        """Test getting documents filtered by category"""
        category_id = sample_documents[0].category_id

        response = client.get(
            f"/documents/?category_id={category_id}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert item["category_id"] == category_id

    def test_update_document_success(
        self, client, db_session, authenticated_user, sample_document
    ):
        """Test successful document update"""
        update_data = {
            "title": "Updated Document Title",
            "description": "Updated description",
            "content": "Updated content",
        }

        response = client.put(
            f"/documents/{sample_document.id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]

    def test_update_document_unauthorized(
        self, client, sample_document, other_user_auth
    ):
        """Test updating document by non-owner (should fail unless admin)"""
        update_data = {"title": "Unauthorized Update"}

        response = client.put(
            f"/documents/{sample_document.id}",
            json=update_data,
            headers=other_user_auth["headers"],
        )

        # Should fail unless user has admin permissions
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_update_document_not_found(self, client, authenticated_user):
        """Test updating non-existent document"""
        update_data = {"title": "Updated Title"}

        response = client.put(
            "/documents/999999", json=update_data, headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_document_success(
        self, client, db_session, authenticated_user, sample_document
    ):
        """Test successful document deletion"""
        document_id = sample_document.id

        response = client.delete(
            f"/documents/{document_id}", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify document is deleted
        get_response = client.get(
            f"/documents/{document_id}", headers=authenticated_user["headers"]
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_document_unauthorized(
        self, client, sample_document, other_user_auth
    ):
        """Test deleting document by non-owner (should fail unless admin)"""
        response = client.delete(
            f"/documents/{sample_document.id}", headers=other_user_auth["headers"]
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_change_document_status(
        self, client, db_session, authenticated_admin, sample_document
    ):
        """Test changing document status"""
        status_data = {"status": DocumentStatus.PUBLISHED.value}

        response = client.put(
            f"/documents/{sample_document.id}/status",
            json=status_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DocumentStatus.PUBLISHED.value

    def test_change_document_status_unauthorized(
        self, client, authenticated_user, sample_document
    ):
        """Test changing document status without proper permissions"""
        status_data = {"status": DocumentStatus.PUBLISHED.value}

        response = client.put(
            f"/documents/{sample_document.id}/status",
            json=status_data,
            headers=authenticated_user["headers"],
        )

        # Should fail if user doesn't have document approval permissions
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_document_version_history(
        self, client, db_session, authenticated_user, sample_document
    ):
        """Test document version history tracking"""
        # Update document to create new version
        update_data = {"content": "Updated content v2"}

        response = client.put(
            f"/documents/{sample_document.id}",
            json=update_data,
            headers=authenticated_user["headers"],
        )
        assert response.status_code == status.HTTP_200_OK

        # Get version history
        response = client.get(
            f"/documents/{sample_document.id}/versions",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1  # Should have at least one version

    def test_document_search_advanced(
        self, client, authenticated_user, sample_documents
    ):
        """Test advanced document search functionality"""
        # Search by content
        response = client.get(
            "/documents/search?query=content&search_in=content",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

        # Search with date range
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()

        response = client.get(
            f"/documents/search?created_after={start_date}&created_before={end_date}",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

    def test_document_bulk_operations(
        self, client, authenticated_admin, sample_documents
    ):
        """Test bulk document operations"""
        document_ids = [doc.id for doc in sample_documents[:3]]

        # Bulk status change
        bulk_data = {
            "document_ids": document_ids,
            "status": DocumentStatus.PUBLISHED.value,
        }

        response = client.put(
            "/documents/bulk/status",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["updated_count"] == 3

    def test_document_bulk_delete(self, client, authenticated_admin, sample_documents):
        """Test bulk document deletion"""
        document_ids = [doc.id for doc in sample_documents[-2:]]

        bulk_data = {"document_ids": document_ids}

        response = client.delete(
            "/documents/bulk/delete",
            json=bulk_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted_count"] == 2

    def test_document_file_upload(self, client, authenticated_user, sample_categories):
        """Test document file upload functionality"""
        # Create a mock file
        file_content = b"This is test file content"

        with patch("app.services.file_service.save_file") as mock_save:
            mock_save.return_value = "uploads/test_document.pdf"

            files = {
                "file": (
                    "test_document.pdf",
                    io.BytesIO(file_content),
                    "application/pdf",
                )
            }

            form_data = {
                "title": "Uploaded Document",
                "description": "Document from file upload",
                "category_id": sample_categories[0].id,
            }

            response = client.post(
                "/documents/upload",
                files=files,
                data=form_data,
                headers=authenticated_user["headers"],
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["title"] == form_data["title"]
            assert "file_path" in data

    def test_document_download(
        self, client, authenticated_user, sample_document_with_file
    ):
        """Test document file download"""
        response = client.get(
            f"/documents/{sample_document_with_file.id}/download",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("application/")

    def test_document_approval_workflow(
        self,
        client,
        db_session,
        authenticated_user,
        authenticated_admin,
        sample_document,
    ):
        """Test document approval workflow"""
        # Submit for approval
        response = client.post(
            f"/documents/{sample_document.id}/submit-approval",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DocumentStatus.PENDING_APPROVAL.value

        # Approve document (admin only)
        approval_data = {
            "approved": True,
            "comment": "Document approved for publication",
        }

        response = client.post(
            f"/documents/{sample_document.id}/approve",
            json=approval_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DocumentStatus.APPROVED.value

    def test_document_rejection_workflow(
        self, client, authenticated_admin, sample_document
    ):
        """Test document rejection workflow"""
        # Submit for approval first
        sample_document.status = DocumentStatus.PENDING_APPROVAL

        rejection_data = {"approved": False, "comment": "Document needs revision"}

        response = client.post(
            f"/documents/{sample_document.id}/approve",
            json=approval_data,
            headers=authenticated_admin["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == DocumentStatus.REJECTED.value

    def test_document_metrics(self, client, authenticated_admin, sample_documents):
        """Test document metrics and statistics"""
        response = client.get(
            "/documents/metrics", headers=authenticated_admin["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_documents" in data
        assert "by_status" in data
        assert "by_category" in data
        assert "recent_activity" in data

    def test_my_documents(self, client, authenticated_user, sample_documents):
        """Test getting current user's documents"""
        response = client.get(
            "/documents/my-documents", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        # All returned documents should belong to the current user
        for item in data["items"]:
            assert item["created_by"] == authenticated_user["user"].id

    def test_document_sharing(
        self, client, db_session, authenticated_user, other_user_auth, sample_document
    ):
        """Test document sharing functionality"""
        share_data = {"user_id": other_user_auth["user"].id, "permission": "read"}

        response = client.post(
            f"/documents/{sample_document.id}/share",
            json=share_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

        # Other user should now be able to access the document
        response = client.get(
            f"/documents/{sample_document.id}", headers=other_user_auth["headers"]
        )

        assert response.status_code == status.HTTP_200_OK

    def test_document_tags(
        self, client, db_session, authenticated_user, sample_document
    ):
        """Test document tagging functionality"""
        tags_data = {"tags": ["important", "policy", "2024"]}

        response = client.post(
            f"/documents/{sample_document.id}/tags",
            json=tags_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

        # Search documents by tag
        response = client.get(
            "/documents/?tags=important", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) >= 1

    def test_document_comments(
        self, client, db_session, authenticated_user, other_user_auth, sample_document
    ):
        """Test document commenting functionality"""
        comment_data = {
            "content": "This is a great document!",
            "document_id": sample_document.id,
        }

        response = client.post(
            "/documents/comments/",
            json=comment_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK

        # Get document comments
        response = client.get(
            f"/documents/{sample_document.id}/comments",
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["content"] == comment_data["content"]

    def test_document_unauthorized_access(self, client, sample_document):
        """Test accessing documents without authentication"""
        response = client.get(f"/documents/{sample_document.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_document_validation_errors(
        self, client, authenticated_user, sample_categories
    ):
        """Test various document validation scenarios"""
        # Test title too long
        invalid_data = {
            "title": "A" * 301,  # Assuming 300 char limit
            "category_id": sample_categories[0].id,
            "content": "Test content",
        }

        response = client.post(
            "/documents/", json=invalid_data, headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test invalid status value
        invalid_status_data = {
            "title": "Test Doc",
            "category_id": sample_categories[0].id,
            "content": "Test content",
            "status": "invalid_status",
        }

        response = client.post(
            "/documents/",
            json=invalid_status_data,
            headers=authenticated_user["headers"],
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
