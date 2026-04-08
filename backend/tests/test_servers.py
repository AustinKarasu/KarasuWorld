"""Server endpoint tests"""
import pytest
import uuid

class TestServers:
    """Test server CRUD operations"""

    @pytest.fixture(scope="class")
    def auth_token(self, base_url, api_client, admin_credentials):
        """Get auth token for tests"""
        response = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Auth headers with token"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_create_server(self, base_url, api_client, auth_headers):
        """Test POST /api/servers - create server"""
        payload = {
            "name": f"TEST_Server_{uuid.uuid4().hex[:6]}",
            "description": "Test server for automated testing",
            "icon_letter": "T"
        }
        response = api_client.post(f"{base_url}/api/servers", json=payload, headers=auth_headers)
        print(f"Create server status: {response.status_code}")
        print(f"Create server response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "server" in data
        assert "default_channel_id" in data
        assert data["server"]["name"] == payload["name"]
        assert data["server"]["owner_id"] is not None
        assert "invite_code" in data["server"]
        print("✓ Server created successfully")
        return data["server"]

    def test_list_servers(self, base_url, api_client, auth_headers):
        """Test GET /api/servers - list user's servers"""
        # Create a server first
        create_payload = {
            "name": f"TEST_ListServer_{uuid.uuid4().hex[:6]}",
            "description": "Test"
        }
        create_response = api_client.post(f"{base_url}/api/servers", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 200
        created_server = create_response.json()["server"]
        
        # List servers
        response = api_client.get(f"{base_url}/api/servers", headers=auth_headers)
        print(f"List servers status: {response.status_code}")
        print(f"List servers response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "servers" in data
        assert isinstance(data["servers"], list)
        # Verify created server is in list
        server_ids = [s["server_id"] for s in data["servers"]]
        assert created_server["server_id"] in server_ids, "Created server should be in list"
        print(f"✓ Listed {len(data['servers'])} servers")

    def test_get_server_details(self, base_url, api_client, auth_headers):
        """Test GET /api/servers/:id - get server details"""
        # Create a server first
        create_payload = {
            "name": f"TEST_DetailServer_{uuid.uuid4().hex[:6]}",
            "description": "Test server details"
        }
        create_response = api_client.post(f"{base_url}/api/servers", json=create_payload, headers=auth_headers)
        assert create_response.status_code == 200
        server_id = create_response.json()["server"]["server_id"]
        
        # Get server details
        response = api_client.get(f"{base_url}/api/servers/{server_id}", headers=auth_headers)
        print(f"Get server details status: {response.status_code}")
        print(f"Get server details response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "server" in data
        assert data["server"]["server_id"] == server_id
        assert data["server"]["name"] == create_payload["name"]
        assert "my_role" in data["server"]
        print("✓ Server details retrieved")

    def test_join_server_with_invite(self, base_url, api_client, admin_credentials):
        """Test POST /api/servers/join - join server with invite code"""
        # Create a new user
        new_user_email = f"TEST_joiner_{uuid.uuid4().hex[:8]}@test.com"
        register_payload = {
            "email": new_user_email,
            "password": "TestPass123!",
            "username": f"joiner_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=register_payload)
        assert register_response.status_code == 200
        new_user_token = register_response.json()["access_token"]
        new_user_headers = {"Authorization": f"Bearer {new_user_token}"}
        
        # Admin creates a server
        admin_login = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        create_payload = {
            "name": f"TEST_JoinServer_{uuid.uuid4().hex[:6]}",
            "description": "Test join"
        }
        create_response = api_client.post(f"{base_url}/api/servers", json=create_payload, headers=admin_headers)
        assert create_response.status_code == 200
        invite_code = create_response.json()["server"]["invite_code"]
        server_id = create_response.json()["server"]["server_id"]
        
        # New user joins with invite code
        join_payload = {"invite_code": invite_code}
        response = api_client.post(f"{base_url}/api/servers/join", json=join_payload, headers=new_user_headers)
        print(f"Join server status: {response.status_code}")
        print(f"Join server response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "server" in data
        assert data["server"]["server_id"] == server_id
        
        # Verify user is now a member
        list_response = api_client.get(f"{base_url}/api/servers", headers=new_user_headers)
        assert list_response.status_code == 200
        user_servers = list_response.json()["servers"]
        server_ids = [s["server_id"] for s in user_servers]
        assert server_id in server_ids, "User should see joined server in their list"
        print("✓ User joined server successfully")

    def test_join_server_invalid_invite(self, base_url, api_client, auth_headers):
        """Test joining with invalid invite code"""
        join_payload = {"invite_code": "INVALID_CODE_123"}
        response = api_client.post(f"{base_url}/api/servers/join", json=join_payload, headers=auth_headers)
        print(f"Invalid invite status: {response.status_code}")
        assert response.status_code == 404, "Invalid invite should return 404"
        print("✓ Invalid invite code rejected")
