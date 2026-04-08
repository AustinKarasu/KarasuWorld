"""Channel endpoint tests"""
import pytest
import uuid

class TestChannels:
    """Test channel operations"""

    @pytest.fixture(scope="class")
    def auth_setup(self, base_url, api_client, admin_credentials):
        """Setup auth and create a test server"""
        # Login
        login_response = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create server
        server_payload = {
            "name": f"TEST_ChannelServer_{uuid.uuid4().hex[:6]}",
            "description": "Test channels"
        }
        server_response = api_client.post(f"{base_url}/api/servers", json=server_payload, headers=headers)
        assert server_response.status_code == 200
        server_id = server_response.json()["server"]["server_id"]
        
        return {"token": token, "headers": headers, "server_id": server_id}

    def test_list_server_channels(self, base_url, api_client, auth_setup):
        """Test GET /api/servers/:id/channels"""
        server_id = auth_setup["server_id"]
        headers = auth_setup["headers"]
        
        response = api_client.get(f"{base_url}/api/servers/{server_id}/channels", headers=headers)
        print(f"List channels status: {response.status_code}")
        print(f"List channels response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        assert isinstance(data["channels"], list)
        # Should have at least the default 'general' channel
        assert len(data["channels"]) >= 1
        channel_names = [c["name"] for c in data["channels"]]
        assert "general" in channel_names, "Default general channel should exist"
        print(f"✓ Listed {len(data['channels'])} channels")

    def test_create_channel(self, base_url, api_client, auth_setup):
        """Test POST /api/servers/:id/channels"""
        server_id = auth_setup["server_id"]
        headers = auth_setup["headers"]
        
        channel_payload = {
            "name": f"test-channel-{uuid.uuid4().hex[:6]}",
            "channel_type": "text"
        }
        response = api_client.post(f"{base_url}/api/servers/{server_id}/channels", json=channel_payload, headers=headers)
        print(f"Create channel status: {response.status_code}")
        print(f"Create channel response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "channel" in data
        assert data["channel"]["server_id"] == server_id
        assert data["channel"]["channel_type"] == "text"
        
        # Verify channel appears in list
        list_response = api_client.get(f"{base_url}/api/servers/{server_id}/channels", headers=headers)
        assert list_response.status_code == 200
        channels = list_response.json()["channels"]
        channel_ids = [c["channel_id"] for c in channels]
        assert data["channel"]["channel_id"] in channel_ids
        print("✓ Channel created and verified")
