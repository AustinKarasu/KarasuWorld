"""Voice channel and media upload tests"""
import pytest
import uuid
import base64

class TestVoiceChannels:
    """Test voice channel join/leave/toggle functionality"""

    @pytest.fixture(scope="class")
    def voice_setup(self, base_url, api_client):
        """Create user, server, and voice channel"""
        # Register user
        email = f"TEST_voice_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "VoicePass123!",
            "username": f"voice_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create server (should auto-create voice channel)
        server_payload = {
            "name": f"TEST_VoiceServer_{uuid.uuid4().hex[:6]}",
            "description": "Server for voice testing"
        }
        server_response = api_client.post(f"{base_url}/api/servers", json=server_payload, headers=headers)
        assert server_response.status_code == 200
        server_id = server_response.json()["server"]["server_id"]
        
        # Get channels (should include voice channel)
        channels_response = api_client.get(f"{base_url}/api/servers/{server_id}/channels", headers=headers)
        assert channels_response.status_code == 200
        channels = channels_response.json()["channels"]
        voice_channel = next((ch for ch in channels if ch["channel_type"] == "voice"), None)
        assert voice_channel is not None, "Server should have a voice channel"
        
        return {
            "token": token,
            "user_id": user_id,
            "headers": headers,
            "server_id": server_id,
            "voice_channel_id": voice_channel["channel_id"]
        }

    def test_join_voice_channel(self, base_url, api_client, voice_setup):
        """Test POST /api/channels/:id/voice/join"""
        response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/join",
            headers=voice_setup["headers"]
        )
        print(f"Join voice channel status: {response.status_code}")
        print(f"Join voice channel response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "participants" in data
        assert isinstance(data["participants"], list)
        # User should be in participants
        participant_ids = [p["user_id"] for p in data["participants"]]
        assert voice_setup["user_id"] in participant_ids, "User should be in voice channel"
        print("✓ Joined voice channel successfully")

    def test_get_voice_participants(self, base_url, api_client, voice_setup):
        """Test GET /api/channels/:id/voice/participants"""
        # Join first
        join_response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/join",
            headers=voice_setup["headers"]
        )
        assert join_response.status_code == 200
        
        # Get participants
        response = api_client.get(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/participants",
            headers=voice_setup["headers"]
        )
        print(f"Get voice participants status: {response.status_code}")
        print(f"Get voice participants response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "participants" in data
        participant_ids = [p["user_id"] for p in data["participants"]]
        assert voice_setup["user_id"] in participant_ids
        print(f"✓ Listed {len(data['participants'])} voice participants")

    def test_toggle_voice_mute(self, base_url, api_client, voice_setup):
        """Test POST /api/channels/:id/voice/toggle - mute"""
        # Join first
        join_response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/join",
            headers=voice_setup["headers"]
        )
        assert join_response.status_code == 200
        
        # Toggle mute
        toggle_payload = {"muted": True}
        response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/toggle",
            json=toggle_payload,
            headers=voice_setup["headers"]
        )
        print(f"Toggle voice mute status: {response.status_code}")
        print(f"Toggle voice mute response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "participants" in data
        # Find user in participants and check muted status
        user_participant = next((p for p in data["participants"] if p["user_id"] == voice_setup["user_id"]), None)
        assert user_participant is not None
        assert user_participant["muted"] == True, "User should be muted"
        print("✓ Voice mute toggled successfully")

    def test_toggle_voice_deafen(self, base_url, api_client, voice_setup):
        """Test POST /api/channels/:id/voice/toggle - deafen"""
        # Join first
        join_response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/join",
            headers=voice_setup["headers"]
        )
        assert join_response.status_code == 200
        
        # Toggle deafen
        toggle_payload = {"deafened": True}
        response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/toggle",
            json=toggle_payload,
            headers=voice_setup["headers"]
        )
        print(f"Toggle voice deafen status: {response.status_code}")
        print(f"Toggle voice deafen response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        user_participant = next((p for p in data["participants"] if p["user_id"] == voice_setup["user_id"]), None)
        assert user_participant is not None
        assert user_participant["deafened"] == True, "User should be deafened"
        print("✓ Voice deafen toggled successfully")

    def test_leave_voice_channel(self, base_url, api_client, voice_setup):
        """Test POST /api/channels/:id/voice/leave"""
        # Join first
        join_response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/join",
            headers=voice_setup["headers"]
        )
        assert join_response.status_code == 200
        
        # Leave
        response = api_client.post(
            f"{base_url}/api/channels/{voice_setup['voice_channel_id']}/voice/leave",
            headers=voice_setup["headers"]
        )
        print(f"Leave voice channel status: {response.status_code}")
        print(f"Leave voice channel response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "participants" in data
        # User should NOT be in participants
        participant_ids = [p["user_id"] for p in data["participants"]]
        assert voice_setup["user_id"] not in participant_ids, "User should not be in voice channel after leaving"
        print("✓ Left voice channel successfully")


class TestMediaAndStickers:
    """Test media upload and sticker endpoints"""

    @pytest.fixture(scope="class")
    def auth_user(self, base_url, api_client):
        """Create authenticated user"""
        email = f"TEST_media_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "MediaPass123!",
            "username": f"media_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_stickers(self, base_url, api_client):
        """Test GET /api/stickers - get built-in sticker packs"""
        response = api_client.get(f"{base_url}/api/stickers")
        print(f"Get stickers status: {response.status_code}")
        print(f"Get stickers response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "sticker_packs" in data
        assert isinstance(data["sticker_packs"], list)
        assert len(data["sticker_packs"]) > 0, "Should have at least one sticker pack"
        # Check structure
        first_pack = data["sticker_packs"][0]
        assert "pack" in first_pack
        assert "stickers" in first_pack
        assert isinstance(first_pack["stickers"], list)
        if len(first_pack["stickers"]) > 0:
            sticker = first_pack["stickers"][0]
            assert "id" in sticker
            assert "emoji" in sticker
            assert "name" in sticker
        print(f"✓ Retrieved {len(data['sticker_packs'])} sticker packs")

    def test_upload_media(self, base_url, api_client, auth_user):
        """Test POST /api/upload - upload base64 media"""
        # Create a small test image (1x1 red pixel PNG)
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        
        payload = {
            "data": test_image_base64,
            "filename": "test_image.png",
            "content_type": "image/png"
        }
        response = api_client.post(f"{base_url}/api/upload", json=payload, headers=auth_user)
        print(f"Upload media status: {response.status_code}")
        print(f"Upload media response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "file_id" in data
        assert "url" in data
        assert data["url"].startswith("/api/files/")
        print("✓ Media uploaded successfully")
        return data["file_id"]

    def test_get_uploaded_file(self, base_url, api_client, auth_user):
        """Test GET /api/files/:id - retrieve uploaded file"""
        # Upload first
        test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        upload_payload = {
            "data": test_image_base64,
            "filename": "test_get.png",
            "content_type": "image/png"
        }
        upload_response = api_client.post(f"{base_url}/api/upload", json=upload_payload, headers=auth_user)
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # Get the file
        response = api_client.get(f"{base_url}/api/files/{file_id}")
        print(f"Get file status: {response.status_code}")
        
        assert response.status_code == 200
        assert response.headers.get("content-type") == "image/png"
        assert len(response.content) > 0, "File content should not be empty"
        print("✓ File retrieved successfully")

    def test_upload_invalid_base64(self, base_url, api_client, auth_user):
        """Test upload with invalid base64 data"""
        payload = {
            "data": "INVALID_BASE64!!!",
            "filename": "invalid.png",
            "content_type": "image/png"
        }
        response = api_client.post(f"{base_url}/api/upload", json=payload, headers=auth_user)
        print(f"Invalid upload status: {response.status_code}")
        assert response.status_code == 400, "Invalid base64 should return 400"
        print("✓ Invalid base64 rejected")
