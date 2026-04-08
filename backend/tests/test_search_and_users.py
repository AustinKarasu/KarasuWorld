"""Search and user profile endpoint tests"""
import pytest
import uuid

class TestSearchAndUsers:
    """Test search and user profile operations"""

    @pytest.fixture(scope="class")
    def auth_setup(self, base_url, api_client, admin_credentials):
        """Setup auth for tests"""
        login_response = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        return {
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"}
        }

    def test_search_endpoint(self, base_url, api_client, auth_setup):
        """Test GET /api/search?q=test"""
        headers = auth_setup["headers"]
        
        # Create a server with searchable name
        server_payload = {
            "name": f"TEST_SearchableServer_{uuid.uuid4().hex[:6]}",
            "description": "Test search"
        }
        create_response = api_client.post(f"{base_url}/api/servers", json=server_payload, headers=headers)
        assert create_response.status_code == 200
        
        # Search for it
        response = api_client.get(f"{base_url}/api/search?q=TEST_Searchable", headers=headers)
        print(f"Search status: {response.status_code}")
        print(f"Search response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert "users" in data
        assert "messages" in data
        assert isinstance(data["servers"], list)
        assert isinstance(data["users"], list)
        assert isinstance(data["messages"], list)
        print(f"✓ Search returned {len(data['servers'])} servers, {len(data['users'])} users, {len(data['messages'])} messages")

    def test_update_user_profile(self, base_url, api_client, auth_setup):
        """Test PUT /api/users/me - update user profile"""
        headers = auth_setup["headers"]
        
        update_payload = {
            "bio": f"Updated bio {uuid.uuid4().hex[:8]}",
            "status": "online"
        }
        response = api_client.put(f"{base_url}/api/users/me", json=update_payload, headers=headers)
        print(f"Update profile status: {response.status_code}")
        print(f"Update profile response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert data["user"]["bio"] == update_payload["bio"]
        assert data["user"]["status"] == update_payload["status"]
        
        # Verify update persisted
        me_response = api_client.get(f"{base_url}/api/auth/me", headers=headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["user"]["bio"] == update_payload["bio"]
        print("✓ User profile updated and verified")

    def test_search_users(self, base_url, api_client, auth_setup):
        """Test GET /api/users/search?q=username"""
        headers = auth_setup["headers"]
        
        # Create a user with searchable username
        unique_username = f"TEST_searchuser_{uuid.uuid4().hex[:6]}"
        register_payload = {
            "email": f"TEST_{uuid.uuid4().hex[:8]}@test.com",
            "password": "TestPass123!",
            "username": unique_username
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert register_response.status_code == 200
        
        # Search for the user
        response = api_client.get(f"{base_url}/api/users/search?q={unique_username[:10]}", headers=headers)
        print(f"User search status: {response.status_code}")
        print(f"User search response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        # Verify our user is in results
        usernames = [u["username"] for u in data["users"]]
        assert unique_username in usernames, "Created user should appear in search results"
        print(f"✓ User search returned {len(data['users'])} results")
