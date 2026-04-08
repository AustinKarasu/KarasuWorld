"""Message endpoint tests"""
import pytest
import uuid

class TestMessages:
    """Test message operations"""

    @pytest.fixture(scope="class")
    def channel_setup(self, base_url, api_client, admin_credentials):
        """Setup server and channel for message tests"""
        # Login
        login_response = api_client.post(f"{base_url}/api/auth/login", json=admin_credentials)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create server
        server_payload = {
            "name": f"TEST_MsgServer_{uuid.uuid4().hex[:6]}",
            "description": "Test messages"
        }
        server_response = api_client.post(f"{base_url}/api/servers", json=server_payload, headers=headers)
        assert server_response.status_code == 200
        server_id = server_response.json()["server"]["server_id"]
        default_channel_id = server_response.json()["default_channel_id"]
        
        return {
            "token": token,
            "headers": headers,
            "server_id": server_id,
            "channel_id": default_channel_id
        }

    def test_send_message_in_channel(self, base_url, api_client, channel_setup):
        """Test POST /api/channels/:id/messages"""
        channel_id = channel_setup["channel_id"]
        headers = channel_setup["headers"]
        
        message_payload = {
            "content": f"Test message {uuid.uuid4().hex[:8]}",
            "message_type": "text"
        }
        response = api_client.post(f"{base_url}/api/channels/{channel_id}/messages", json=message_payload, headers=headers)
        print(f"Send message status: {response.status_code}")
        print(f"Send message response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["content"] == message_payload["content"]
        assert data["message"]["channel_id"] == channel_id
        assert "message_id" in data["message"]
        print("✓ Message sent successfully")
        return data["message"]

    def test_get_channel_messages(self, base_url, api_client, channel_setup):
        """Test GET /api/channels/:id/messages"""
        channel_id = channel_setup["channel_id"]
        headers = channel_setup["headers"]
        
        # Send a message first
        message_payload = {
            "content": f"Test get messages {uuid.uuid4().hex[:8]}",
            "message_type": "text"
        }
        send_response = api_client.post(f"{base_url}/api/channels/{channel_id}/messages", json=message_payload, headers=headers)
        assert send_response.status_code == 200
        sent_message_id = send_response.json()["message"]["message_id"]
        
        # Get messages
        response = api_client.get(f"{base_url}/api/channels/{channel_id}/messages", headers=headers)
        print(f"Get messages status: {response.status_code}")
        print(f"Get messages response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
        # Verify sent message is in list
        message_ids = [m["message_id"] for m in data["messages"]]
        assert sent_message_id in message_ids, "Sent message should appear in messages list"
        print(f"✓ Retrieved {len(data['messages'])} messages")

    def test_add_reaction_to_message(self, base_url, api_client, channel_setup):
        """Test POST /api/messages/:id/react"""
        channel_id = channel_setup["channel_id"]
        headers = channel_setup["headers"]
        
        # Send a message first
        message_payload = {
            "content": f"Test reaction {uuid.uuid4().hex[:8]}",
            "message_type": "text"
        }
        send_response = api_client.post(f"{base_url}/api/channels/{channel_id}/messages", json=message_payload, headers=headers)
        assert send_response.status_code == 200
        message_id = send_response.json()["message"]["message_id"]
        
        # Add reaction
        reaction_payload = {"emoji": "👍"}
        response = api_client.post(f"{base_url}/api/messages/{message_id}/react", json=reaction_payload, headers=headers)
        print(f"Add reaction status: {response.status_code}")
        print(f"Add reaction response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "reactions" in data
        assert isinstance(data["reactions"], list)
        assert len(data["reactions"]) > 0
        assert data["reactions"][0]["emoji"] == "👍"
        assert data["reactions"][0]["count"] == 1
        print("✓ Reaction added successfully")
