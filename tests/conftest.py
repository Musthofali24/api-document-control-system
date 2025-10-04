"""
Test configuration and fixtures
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import patch

# Set testing environment before importing app
os.environ["TESTING"] = "true"

from app.config.database import Base, get_db
from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.category import Category
from app.models.document import Document
from app.models.notification import Notification
from app.core.auth import get_password_hash, create_access_token
from app.main import app


# Test database URL - using SQLite for testing
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test"""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with test database"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        name="Test User",
        email="test@example.com",
        password=get_password_hash("testpass123"),
        email_verified_at=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session):
    """Create an admin test user"""
    user = User(
        name="Admin User",
        email="admin@example.com",
        password=get_password_hash("adminpass123"),
        email_verified_at=None,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_role(db_session):
    """Create a test role"""
    role = Role(name="Test Role", slug="test-role", description="A test role")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def admin_role(db_session):
    """Create an admin role"""
    role = Role(name="Admin", slug="admin", description="Administrator role")
    db_session.add(role)
    db_session.commit()
    db_session.refresh(role)
    return role


@pytest.fixture
def test_permission(db_session):
    """Create a test permission"""
    permission = Permission(slug="test-permission", description="A test permission")
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


@pytest.fixture
def admin_permission(db_session):
    """Create an admin permission"""
    permission = Permission(slug="admin-all", description="Full admin access")
    db_session.add(permission)
    db_session.commit()
    db_session.refresh(permission)
    return permission


@pytest.fixture
def test_category(db_session):
    """Create a test category"""
    category = Category(name="Test Category", description="A test category")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def authenticated_user(test_user):
    """Create access token for test user"""
    token = create_access_token(
        data={"sub": str(test_user.id), "email": test_user.email}
    )
    return {
        "user": test_user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
def authenticated_admin(admin_user, admin_role, admin_permission, db_session):
    """Create authenticated admin user with role and permissions"""
    # Assign admin role to user
    admin_user.roles.append(admin_role)

    # Assign admin permission to role
    admin_role.permissions.append(admin_permission)

    db_session.commit()

    token = create_access_token(
        data={"sub": str(admin_user.id), "email": admin_user.email}
    )
    return {
        "user": admin_user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
def sample_users(db_session):
    """Create multiple sample users for testing"""
    users = []
    for i in range(5):
        user = User(
            name=f"User {i+1}",
            email=f"user{i+1}@example.com",
            password=get_password_hash(f"password{i+1}"),
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)

    return users


@pytest.fixture
def sample_roles(db_session):
    """Create multiple sample roles for testing"""
    roles = []
    role_names = ["Manager", "Editor", "Viewer", "Moderator"]

    for name in role_names:
        role = Role(
            name=name, slug=name.lower(), description=f"{name} role description"
        )
        db_session.add(role)
        roles.append(role)

    db_session.commit()
    for role in roles:
        db_session.refresh(role)

    return roles


@pytest.fixture
def sample_permissions(db_session):
    """Create multiple sample permissions for testing"""
    permissions = []
    permission_slugs = [
        "users.create",
        "users.read",
        "users.update",
        "users.delete",
        "documents.create",
        "documents.read",
        "documents.update",
        "documents.delete",
        "roles.assign",
        "permissions.grant",
    ]

    for slug in permission_slugs:
        permission = Permission(
            slug=slug,
            description=f"Permission to {slug.replace('.', ' ').replace('_', ' ')}",
        )
        db_session.add(permission)
        permissions.append(permission)

    db_session.commit()
    for permission in permissions:
        db_session.refresh(permission)

    return permissions


# Helper functions for tests
def create_test_document(db_session, user_id, category_id, title="Test Document"):
    """Helper to create test document"""
    document = Document(
        title=title,
        description="Test document description",
        file_path="/test/path/document.pdf",
        uploaded_by=user_id,
        category_id=category_id,
        status="draft",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def create_test_notification(db_session, user_id, notification_type="test"):
    """Helper to create test notification"""
    import uuid

    notification = Notification(
        id=str(uuid.uuid4()),
        type=notification_type,
        notifiable_type="App\\Models\\User",
        notifiable_id=user_id,
        data='{"title": "Test Notification", "message": "This is a test"}',
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return notification


# Test data constants
TEST_USER_DATA = {
    "name": "New User",
    "email": "newuser@example.com",
    "password": "newpassword123",
}

TEST_ROLE_DATA = {
    "name": "New Role",
    "slug": "new-role",
    "description": "A newly created role",
}

TEST_PERMISSION_DATA = {
    "slug": "new-permission",
    "description": "A newly created permission",
}

TEST_NOTIFICATION_DATA = {
    "type": "test_notification",
    "title": "Test Notification",
    "message": "This is a test notification",
    "action_url": "/test/action",
}
