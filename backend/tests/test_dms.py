"""Direct message endpoint tests"""
import pytest
import uuid

class TestDMs:
    """Test direct message operations"""

    @pytest.fixture(scope="class")
    def two_users_setup(self, base_url, api_client):
        """Create two users for DM testing"""
        # Create user 1
        user1_email = f"TEST_dm_user1_{uuid.uuid4().hex[:8]}@test.com"
        user1_payload = {
            "email": user1_email,
            "password": "TestPass123!",
            "username": f"dmuser1_{uuid.uuid4().hex[:6]}"
        }
        user1_response = api_client.post(f"{base_url}/api/auth/register", json=user1_payload)
        assert user1_response.status_code == 200
        user1_data = user1_response.json()
        
        # Create user 2
        user2_email = f"TEST_dm_user2_{uuid.uuid4().hex[:8]}@test.com"
        user2_payload = {
            "email": user2_email,
            "password": "TestPass123!",
            "username": f"dmuser2_{uuid.uuid4().hex[:6]}"
        }
        user2_response = api_client.post(f"{base_url}/api/auth/register", json=user2_payload)
        assert user2_response.status_code == 200
        user2_data = user2_response.json()
        
        return {
            "user1": {
                "user_id": user1_data["user"]["user_id"],
                "token": user1_data["access_token"],
                "headers": {"Authorization": f"Bearer {user1_data['access_token']}"}
            },
            "user2": {
                "user_id": user2_data["user"]["user_id"],
                "token": user2_data["access_token"],
                "headers": {"Authorization": f"Bearer {user2_data['access_token']}"}
            }
        }

    def test_create_dm(self, base_url, api_client, two_users_setup):
        """Test POST /api/dms - create DM conversation"""
        user1 = two_users_setup["user1"]
        user2 = two_users_setup["user2"]
        
        dm_payload = {"recipient_id": user2["user_id"]}
        response = api_client.post(f"{base_url}/api/dms", json=dm_payload, headers=user1["headers"])
        print(f"Create DM status: {response.status_code}")
        print(f"Create DM response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "dm" in data
        assert "dm_id" in data["dm"]
        assert "participants" in data["dm"]
        assert user1["user_id"] in data["dm"]["participants"]
        assert user2["user_id"] in data["dm"]["participants"]
        print("✓ DM conversation created")
        return data["dm"]

    def test_list_dms(self, base_url, api_client, two_users_setup):
        """Test GET /api/dms - list user's DM conversations"""
        user1 = two_users_setup["user1"]
        user2 = two_users_setup["user2"]
        
        # Create a DM first
        dm_payload = {"recipient_id": user2["user_id"]}
        create_response = api_client.post(f"{base_url}/api/dms", json=dm_payload, headers=user1["headers"])
        assert create_response.status_code == 200
        created_dm_id = create_response.json()["dm"]["dm_id"]
        
        # List DMs
        response = api_client.get(f"{base_url}/api/dms", headers=user1["headers"])
        print(f"List DMs status: {response.status_code}")
        print(f"List DMs response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "dms" in data
        assert isinstance(data["dms"], list)
        # Verify created DM is in list
        dm_ids = [dm["dm_id"] for dm in data["dms"]]
        assert created_dm_id in dm_ids, "Created DM should be in list"
        print(f"✓ Listed {len(data['dms'])} DM conversations")

    def test_send_dm_message(self, base_url, api_client, two_users_setup):
        """Test POST /api/dms/:id/messages - send DM message"""
        user1 = two_users_setup["user1"]
        user2 = two_users_setup["user2"]
        
        # Create DM
        dm_payload = {"recipient_id": user2["user_id"]}
        create_response = api_client.post(f"{base_url}/api/dms", json=dm_payload, headers=user1["headers"])
        assert create_response.status_code == 200
        dm_id = create_response.json()["dm"]["dm_id"]
        
        # Send message
        message_payload = {
            "content": f"Test DM message {uuid.uuid4().hex[:8]}",
            "message_type": "text"
        }
        response = api_client.post(f"{base_url}/api/dms/{dm_id}/messages", json=message_payload, headers=user1["headers"])
        print(f"Send DM message status: {response.status_code}")
        print(f"Send DM message response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"]["content"] == message_payload["content"]
        assert data["message"]["dm_id"] == dm_id
        print("✓ DM message sent successfully")

    def test_get_dm_messages(self, base_url, api_client, two_users_setup):
        """Test GET /api/dms/:id/messages - get DM messages"""
        user1 = two_users_setup["user1"]
        user2 = two_users_setup["user2"]
        
        # Create DM
        dm_payload = {"recipient_id": user2["user_id"]}
        create_response = api_client.post(f"{base_url}/api/dms", json=dm_payload, headers=user1["headers"])
        assert create_response.status_code == 200
        dm_id = create_response.json()["dm"]["dm_id"]
        
        # Send a message
        message_payload = {
            "content": f"Test get DM messages {uuid.uuid4().hex[:8]}",
            "message_type": "text"
        }
        send_response = api_client.post(f"{base_url}/api/dms/{dm_id}/messages", json=message_payload, headers=user1["headers"])
        assert send_response.status_code == 200
        sent_message_id = send_response.json()["message"]["message_id"]
        
        # Get messages
        response = api_client.get(f"{base_url}/api/dms/{dm_id}/messages", headers=user1["headers"])
        print(f"Get DM messages status: {response.status_code}")
        print(f"Get DM messages response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert isinstance(data["messages"], list)
        # Verify sent message is in list
        message_ids = [m["message_id"] for m in data["messages"]]
        assert sent_message_id in message_ids, "Sent DM message should appear in messages list"
        print(f"✓ Retrieved {len(data['messages'])} DM messages")
