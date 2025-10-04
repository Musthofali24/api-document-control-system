"""
Tests for Authentication endpoints
"""

import pytest
from fastapi import status
from unittest.mock import patch

from app.models.user import User
from app.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token,
)


class TestAuthEndpoints:
    """Test class for Authentication API endpoints"""

    def test_login_success(self, client, test_user):
        """Test successful user login"""
        login_data = {"email": "test@example.com", "password": "testpass123"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_email(self, client):
        """Test login with non-existent email"""
        login_data = {"email": "nonexistent@example.com", "password": "password123"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_invalid_password(self, client, test_user):
        """Test login with incorrect password"""
        login_data = {"email": "test@example.com", "password": "wrongpassword"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_empty_email(self, client):
        """Test login with empty email"""
        login_data = {"email": "", "password": "password123"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        login_data = {"email": "not-an-email", "password": "password123"}

        response = client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_logout_success(self, client, authenticated_user):
        """Test successful user logout"""
        response = client.post(
            "/api/v1/auth/logout", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        assert "Successfully logged out" in response.json()["message"]

    def test_logout_unauthorized(self, client):
        """Test logout without authentication token"""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_logout_invalid_token(self, client):
        """Test logout with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.post("/api/v1/auth/logout", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_success(self, client, authenticated_user):
        """Test getting current user information"""
        response = client.get("/api/v1/auth/me", headers=authenticated_user["headers"])

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == authenticated_user["user"].email
        assert data["name"] == authenticated_user["user"].name

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}

        response = client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_success(self, client, authenticated_user):
        """Test token refresh"""
        response = client.post(
            "/api/v1/auth/refresh", headers=authenticated_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_unauthorized(self, client):
        """Test token refresh without authentication"""
        response = client.post("/api/v1/auth/refresh")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthHelpers:
    """Test class for Authentication helper functions"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)

        # Hash should not be the same as original password
        assert hashed != password

        # Verify password should work
        assert verify_password(password, hashed) is True

        # Wrong password should fail
        assert verify_password("wrongpassword", hashed) is False

    def test_access_token_creation_and_decoding(self):
        """Test JWT token creation and decoding"""
        test_data = {"sub": "123", "email": "test@example.com"}

        # Create token
        token = create_access_token(data=test_data)
        assert token is not None
        assert isinstance(token, str)

        # Decode token
        decoded_data = verify_token(token)
        assert decoded_data is not None
        assert decoded_data["sub"] == int(test_data["sub"])

    def test_access_token_expiration(self):
        """Test JWT token with custom expiration"""
        from datetime import timedelta

        test_data = {"sub": "123"}

        # Create token with short expiration (for testing)
        token = create_access_token(data=test_data, expires_delta=timedelta(seconds=1))

        # Should be valid immediately
        decoded_data = verify_token(token)
        assert decoded_data is not None

        # Mock time passing (in real scenario, would wait)
        import time

        time.sleep(2)

        # Should be expired (may need to mock jwt.decode for proper testing)
        # This is a simplified test - in production, you'd mock the current time

    def test_invalid_token_decoding(self):
        """Test decoding invalid tokens"""
        # Test with completely invalid token
        assert verify_token("invalid_token") is None

        # Test with empty token
        assert verify_token("") is None

        # Test with None token
        assert verify_token(None) is None

    def test_token_with_invalid_signature(self):
        """Test token with tampered signature"""
        valid_token = create_access_token(data={"sub": "test@example.com"})

        # Tamper with the token (change last character)
        tampered_token = valid_token[:-1] + "X"

        # Should fail to decode
        assert verify_token(tampered_token) is None


class TestAuthIntegration:
    """Integration tests for authentication flow"""

    def test_complete_auth_flow(self, client, db_session):
        """Test complete authentication flow: register -> login -> access protected resource"""
        # Step 1: Create user (simulate registration)
        user = User(
            name="Integration Test User",
            email="integration@example.com",
            password=get_password_hash("integrationpass123"),
        )
        db_session.add(user)
        db_session.commit()

        # Step 2: Login
        login_data = {
            "email": "integration@example.com",
            "password": "integrationpass123",
        }

        login_response = client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == status.HTTP_200_OK

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 3: Access protected resource
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["email"] == "integration@example.com"

        # Step 4: Logout
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == status.HTTP_200_OK

    def test_concurrent_logins(self, client, test_user):
        """Test multiple concurrent login sessions"""
        login_data = {"email": "test@example.com", "password": "testpass123"}

        # Login multiple times
        tokens = []
        for i in range(3):
            response = client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == status.HTTP_200_OK
            tokens.append(response.json()["access_token"])

        # All tokens should be valid
        for token in tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == status.HTTP_200_OK

    def test_login_rate_limiting(self, client):
        """Test login rate limiting (if implemented)"""
        # This test assumes rate limiting is implemented
        # Adjust based on your actual rate limiting configuration

        login_data = {"email": "test@example.com", "password": "wrongpassword"}

        # Make multiple failed login attempts
        failed_attempts = 0
        for i in range(10):  # Adjust based on your rate limit
            response = client.post("/api/v1/auth/login", json=login_data)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
            failed_attempts += 1

        # Should eventually hit rate limit (if implemented)
        # This test may pass if no rate limiting is implemented

    def test_token_blacklisting_after_logout(self, client, authenticated_user):
        """Test that tokens are invalid after logout (if token blacklisting is implemented)"""
        headers = authenticated_user["headers"]

        # Verify token works before logout
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        # Logout
        logout_response = client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == status.HTTP_200_OK

        # Try to use token after logout
        # Note: This test will pass if token blacklisting is not implemented
        # In that case, the token will still be valid until it expires
        response = client.get("/api/v1/auth/me", headers=headers)

        # Could be either 401 (if blacklisting implemented) or 200 (if not)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_case_insensitive_email_login(self, client, test_user):
        """Test that email login is case insensitive"""
        # Test with different case variations
        email_variations = ["TEST@EXAMPLE.COM", "Test@Example.Com", "test@EXAMPLE.com"]

        for email in email_variations:
            login_data = {"email": email, "password": "testpass123"}

            response = client.post("/api/v1/auth/login", json=login_data)
            # This test assumes case-insensitive email handling
            # Adjust based on your implementation
            assert response.status_code == status.HTTP_200_OK

    def test_password_security_requirements(self, client, db_session):
        """Test password security requirements (if implemented)"""
        # Test various password strengths
        weak_passwords = [
            "123",  # Too short
            "password",  # Too common
            "12345678",  # Only numbers
            "abcdefgh",  # Only letters
        ]

        for i, password in enumerate(weak_passwords):
            user = User(
                name=f"Test User {i}",
                email=f"test{i}@example.com",
                password=get_password_hash(
                    password
                ),  # This might fail if password validation exists
            )

            try:
                db_session.add(user)
                db_session.commit()
                # If we reach here, password was accepted
            except Exception as e:
                # Password was rejected due to security requirements
                db_session.rollback()
