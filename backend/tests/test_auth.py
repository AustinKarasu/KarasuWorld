"""Authentication endpoint tests"""
import pytest
import requests
import uuid

class TestAuth:
    """Test authentication flows"""

    def test_register_new_user(self, base_url, api_client):
        """Test user registration with unique email"""
        unique_email = f"TEST_user_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": unique_email,
            "password": "TestPass123!",
            "username": f"testuser_{uuid.uuid4().hex[:6]}"
        }
        response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        print(f"Register response status: {response.status_code}")
        print(f"Register response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user" in data, "Response should contain user object"
        assert "access_token" in data, "Response should contain access_token"
        assert "refresh_token" in data, "Response should contain refresh_token"
        assert data["user"]["email"] == unique_email.lower(), "Email should match (lowercase)"
        print("✓ User registration successful")

    def test_register_duplicate_email(self, base_url, api_client):
        """Test registration with duplicate email fails"""
        unique_email = f"TEST_dup_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": unique_email,
            "password": "TestPass123!",
            "username": f"testuser_{uuid.uuid4().hex[:6]}"
        }
        # First registration
        response1 = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert response1.status_code == 200
        
        # Duplicate registration
        payload["username"] = f"testuser_{uuid.uuid4().hex[:6]}"  # Different username
        response2 = api_client.post(f"{base_url}/api/auth/register", json=payload)
        print(f"Duplicate register status: {response2.status_code}")
        assert response2.status_code == 400, "Duplicate email should return 400"
        print("✓ Duplicate email validation working")

    def test_login_admin(self, base_url, api_client, admin_credentials):
        """Test admin login"""
        response = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        print(f"Admin login status: {response.status_code}")
        print(f"Admin login response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["email"] == admin_credentials["email"]
        assert data["user"]["role"] == "admin"
        print("✓ Admin login successful")

    def test_login_invalid_credentials(self, base_url, api_client):
        """Test login with invalid credentials"""
        payload = {
            "email": "nonexistent@test.com",
            "password": "wrongpassword"
        }
        response = api_client.post(f"{base_url}/api/auth/login", json=payload)
        print(f"Invalid login status: {response.status_code}")
        assert response.status_code == 401, "Invalid credentials should return 401"
        print("✓ Invalid credentials rejected")

    def test_get_current_user(self, base_url, api_client, admin_credentials):
        """Test GET /api/auth/me with valid token"""
        # Login first
        login_response = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get current user
        headers = {"Authorization": f"Bearer {token}"}
        response = api_client.get(f"{base_url}/api/auth/me", headers=headers)
        print(f"Get me status: {response.status_code}")
        print(f"Get me response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == admin_credentials["email"]
        print("✓ Get current user successful")

    def test_get_current_user_no_token(self, base_url, api_client):
        """Test GET /api/auth/me without token"""
        response = api_client.get(f"{base_url}/api/auth/me")
        print(f"Get me no token status: {response.status_code}")
        assert response.status_code == 401, "Should return 401 without token"
        print("✓ Auth required for /api/auth/me")
