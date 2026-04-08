"""E2E encryption, push notifications, and message deletion tests"""
import pytest
import uuid

class TestE2EEncryption:
    """Test E2E key exchange for DMs"""

    @pytest.fixture(scope="class")
    def dm_setup(self, base_url, api_client):
        """Create two users and a DM conversation"""
        # User 1
        email1 = f"TEST_e2e1_{uuid.uuid4().hex[:8]}@test.com"
        user1_payload = {
            "email": email1,
            "password": "E2EPass123!",
            "username": f"e2e1_{uuid.uuid4().hex[:6]}"
        }
        user1_register = api_client.post(f"{base_url}/api/auth/register", json=user1_payload)
        assert user1_register.status_code == 200
        user1_token = user1_register.json()["access_token"]
        user1_id = user1_register.json()["user"]["user_id"]
        user1_headers = {"Authorization": f"Bearer {user1_token}"}
        
        # User 2
        email2 = f"TEST_e2e2_{uuid.uuid4().hex[:8]}@test.com"
        user2_payload = {
            "email": email2,
            "password": "E2EPass123!",
            "username": f"e2e2_{uuid.uuid4().hex[:6]}"
        }
        user2_register = api_client.post(f"{base_url}/api/auth/register", json=user2_payload)
        assert user2_register.status_code == 200
        user2_token = user2_register.json()["access_token"]
        user2_id = user2_register.json()["user"]["user_id"]
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        
        # Create DM
        dm_payload = {"recipient_id": user2_id}
        dm_response = api_client.post(f"{base_url}/api/dms", json=dm_payload, headers=user1_headers)
        assert dm_response.status_code == 200
        dm_id = dm_response.json()["dm"]["dm_id"]
        
        return {
            "user1_headers": user1_headers,
            "user2_headers": user2_headers,
            "user1_id": user1_id,
            "user2_id": user2_id,
            "dm_id": dm_id
        }

    def test_exchange_e2e_key(self, base_url, api_client, dm_setup):
        """Test POST /api/dms/:id/keys - exchange public key"""
        payload = {"public_key": "TEST_PUBLIC_KEY_USER1_BASE64"}
        response = api_client.post(
            f"{base_url}/api/dms/{dm_setup['dm_id']}/keys",
            json=payload,
            headers=dm_setup["user1_headers"]
        )
        print(f"Exchange E2E key status: {response.status_code}")
        print(f"Exchange E2E key response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "key_stored"
        print("✓ E2E key exchanged successfully")

    def test_get_e2e_keys(self, base_url, api_client, dm_setup):
        """Test GET /api/dms/:id/keys - get all public keys"""
        # User1 stores key
        key1_payload = {"public_key": "USER1_PUBLIC_KEY"}
        api_client.post(
            f"{base_url}/api/dms/{dm_setup['dm_id']}/keys",
            json=key1_payload,
            headers=dm_setup["user1_headers"]
        )
        
        # User2 stores key
        key2_payload = {"public_key": "USER2_PUBLIC_KEY"}
        api_client.post(
            f"{base_url}/api/dms/{dm_setup['dm_id']}/keys",
            json=key2_payload,
            headers=dm_setup["user2_headers"]
        )
        
        # Get all keys
        response = api_client.get(
            f"{base_url}/api/dms/{dm_setup['dm_id']}/keys",
            headers=dm_setup["user1_headers"]
        )
        print(f"Get E2E keys status: {response.status_code}")
        print(f"Get E2E keys response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data
        assert isinstance(data["keys"], list)
        assert len(data["keys"]) == 2, "Should have keys from both users"
        # Verify keys
        public_keys = [k["public_key"] for k in data["keys"]]
        assert "USER1_PUBLIC_KEY" in public_keys
        assert "USER2_PUBLIC_KEY" in public_keys
        print("✓ E2E keys retrieved successfully")


class TestPushNotifications:
    """Test push notification registration"""

    @pytest.fixture(scope="class")
    def auth_user(self, base_url, api_client):
        """Create authenticated user"""
        email = f"TEST_push_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "PushPass123!",
            "username": f"push_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_register_push_token(self, base_url, api_client, auth_user):
        """Test POST /api/push/register - register Expo push token"""
        payload = {
            "push_token": "ExponentPushToken[TEST_TOKEN_123]",
            "device_type": "expo"
        }
        response = api_client.post(f"{base_url}/api/push/register", json=payload, headers=auth_user)
        print(f"Register push token status: {response.status_code}")
        print(f"Register push token response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "registered"
        print("✓ Push token registered successfully")

    def test_register_push_token_update(self, base_url, api_client, auth_user):
        """Test updating push token (upsert)"""
        # Register first token
        payload1 = {
            "push_token": "ExponentPushToken[FIRST_TOKEN]",
            "device_type": "expo"
        }
        response1 = api_client.post(f"{base_url}/api/push/register", json=payload1, headers=auth_user)
        assert response1.status_code == 200
        
        # Update with new token
        payload2 = {
            "push_token": "ExponentPushToken[UPDATED_TOKEN]",
            "device_type": "expo"
        }
        response2 = api_client.post(f"{base_url}/api/push/register", json=payload2, headers=auth_user)
        print(f"Update push token status: {response2.status_code}")
        assert response2.status_code == 200
        print("✓ Push token updated successfully")


class TestMessageDeletion:
    """Test message deletion functionality"""

    @pytest.fixture(scope="class")
    def message_setup(self, base_url, api_client):
        """Create user, server, channel, and message"""
        # Register user
        email = f"TEST_msgdel_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "MsgDelPass123!",
            "username": f"msgdel_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create server
        server_payload = {
            "name": f"TEST_MsgDelServer_{uuid.uuid4().hex[:6]}",
            "description": "Server for message deletion testing"
        }
        server_response = api_client.post(f"{base_url}/api/servers", json=server_payload, headers=headers)
        assert server_response.status_code == 200
        server_id = server_response.json()["server"]["server_id"]
        
        # Get default channel
        channels_response = api_client.get(f"{base_url}/api/servers/{server_id}/channels", headers=headers)
        assert channels_response.status_code == 200
        channels = channels_response.json()["channels"]
        text_channel = next((ch for ch in channels if ch["channel_type"] == "text"), None)
        assert text_channel is not None
        channel_id = text_channel["channel_id"]
        
        # Send a message
        msg_payload = {
            "content": "Test message to delete",
            "message_type": "text"
        }
        msg_response = api_client.post(f"{base_url}/api/channels/{channel_id}/messages", json=msg_payload, headers=headers)
        assert msg_response.status_code == 200
        message_id = msg_response.json()["message"]["message_id"]
        
        return {
            "headers": headers,
            "user_id": user_id,
            "server_id": server_id,
            "channel_id": channel_id,
            "message_id": message_id
        }

    def test_delete_own_message(self, base_url, api_client, message_setup):
        """Test DELETE /api/messages/:id - delete own message"""
        response = api_client.delete(
            f"{base_url}/api/messages/{message_setup['message_id']}",
            headers=message_setup["headers"]
        )
        print(f"Delete message status: {response.status_code}")
        print(f"Delete message response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "deleted"
        
        # Verify message is deleted (should not appear in channel messages)
        messages_response = api_client.get(
            f"{base_url}/api/channels/{message_setup['channel_id']}/messages",
            headers=message_setup["headers"]
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()["messages"]
        message_ids = [m["message_id"] for m in messages]
        assert message_setup["message_id"] not in message_ids, "Deleted message should not appear"
        print("✓ Message deleted successfully")

    def test_delete_message_not_owner(self, base_url, api_client, message_setup):
        """Test that non-owner cannot delete message without permissions"""
        # Create another user
        other_email = f"TEST_other_{uuid.uuid4().hex[:8]}@test.com"
        other_payload = {
            "email": other_email,
            "password": "OtherPass123!",
            "username": f"other_{uuid.uuid4().hex[:6]}"
        }
        other_register = api_client.post(f"{base_url}/api/auth/register", json=other_payload)
        assert other_register.status_code == 200
        other_token = other_register.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}
        
        # Try to delete message as other user (should fail - not a member)
        response = api_client.delete(
            f"{base_url}/api/messages/{message_setup['message_id']}",
            headers=other_headers
        )
        print(f"Delete other's message status: {response.status_code}")
        # Should fail with 403 or 404 (not a member of server)
        assert response.status_code in [403, 404], "Non-owner should not be able to delete message"
        print("✓ Message deletion permission check working")
