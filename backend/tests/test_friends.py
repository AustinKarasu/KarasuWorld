"""Friend system endpoint tests"""
import pytest
import uuid

class TestFriends:
    """Test friend system - send request, accept, decline, list"""

    @pytest.fixture(scope="class")
    def user1_auth(self, base_url, api_client):
        """Create and login user 1"""
        email = f"TEST_friend1_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "FriendPass123!",
            "username": f"friend1_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["user_id"]
        return {"token": token, "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}

    @pytest.fixture(scope="class")
    def user2_auth(self, base_url, api_client):
        """Create and login user 2"""
        email = f"TEST_friend2_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "FriendPass123!",
            "username": f"friend2_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["user_id"]
        return {"token": token, "user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}

    def test_send_friend_request(self, base_url, api_client, user1_auth, user2_auth):
        """Test POST /api/friends/request - send friend request"""
        payload = {"target_user_id": user2_auth["user_id"]}
        response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        print(f"Send friend request status: {response.status_code}")
        print(f"Send friend request response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "friendship_id" in data
        assert data["status"] == "pending"
        print("✓ Friend request sent successfully")
        return data["friendship_id"]

    def test_list_friend_requests_incoming(self, base_url, api_client, user1_auth, user2_auth):
        """Test GET /api/friends/requests - list incoming requests"""
        # User1 sends request to User2
        payload = {"target_user_id": user2_auth["user_id"]}
        send_response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        assert send_response.status_code == 200
        friendship_id = send_response.json()["friendship_id"]
        
        # User2 checks incoming requests
        response = api_client.get(f"{base_url}/api/friends/requests", headers=user2_auth["headers"])
        print(f"List friend requests status: {response.status_code}")
        print(f"List friend requests response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "incoming" in data
        assert "outgoing" in data
        assert isinstance(data["incoming"], list)
        # Verify the request is in incoming list
        incoming_ids = [req["friendship_id"] for req in data["incoming"]]
        assert friendship_id in incoming_ids, "Friend request should be in incoming list"
        print("✓ Incoming friend requests listed")

    def test_accept_friend_request(self, base_url, api_client, user1_auth, user2_auth):
        """Test POST /api/friends/:id/accept - accept friend request"""
        # User1 sends request to User2
        payload = {"target_user_id": user2_auth["user_id"]}
        send_response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        assert send_response.status_code == 200
        friendship_id = send_response.json()["friendship_id"]
        
        # User2 accepts the request
        response = api_client.post(f"{base_url}/api/friends/{friendship_id}/accept", headers=user2_auth["headers"])
        print(f"Accept friend request status: {response.status_code}")
        print(f"Accept friend request response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        print("✓ Friend request accepted")

    def test_list_friends(self, base_url, api_client, user1_auth, user2_auth):
        """Test GET /api/friends - list accepted friends"""
        # User1 sends request to User2
        payload = {"target_user_id": user2_auth["user_id"]}
        send_response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        assert send_response.status_code == 200
        friendship_id = send_response.json()["friendship_id"]
        
        # User2 accepts
        accept_response = api_client.post(f"{base_url}/api/friends/{friendship_id}/accept", headers=user2_auth["headers"])
        assert accept_response.status_code == 200
        
        # User1 lists friends
        response = api_client.get(f"{base_url}/api/friends", headers=user1_auth["headers"])
        print(f"List friends status: {response.status_code}")
        print(f"List friends response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "friends" in data
        assert isinstance(data["friends"], list)
        # Verify User2 is in User1's friend list
        friend_ids = [f["user_id"] for f in data["friends"]]
        assert user2_auth["user_id"] in friend_ids, "User2 should be in User1's friend list"
        print(f"✓ Listed {len(data['friends'])} friends")

    def test_decline_friend_request(self, base_url, api_client, user1_auth, user2_auth):
        """Test POST /api/friends/:id/decline - decline friend request"""
        # User1 sends request to User2
        payload = {"target_user_id": user2_auth["user_id"]}
        send_response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        assert send_response.status_code == 200
        friendship_id = send_response.json()["friendship_id"]
        
        # User2 declines the request
        response = api_client.post(f"{base_url}/api/friends/{friendship_id}/decline", headers=user2_auth["headers"])
        print(f"Decline friend request status: {response.status_code}")
        print(f"Decline friend request response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "declined"
        
        # Verify request is no longer in incoming list
        requests_response = api_client.get(f"{base_url}/api/friends/requests", headers=user2_auth["headers"])
        assert requests_response.status_code == 200
        incoming_ids = [req["friendship_id"] for req in requests_response.json()["incoming"]]
        assert friendship_id not in incoming_ids, "Declined request should be removed"
        print("✓ Friend request declined")

    def test_remove_friend(self, base_url, api_client, user1_auth, user2_auth):
        """Test DELETE /api/friends/:id - remove friend"""
        # User1 sends request to User2
        payload = {"target_user_id": user2_auth["user_id"]}
        send_response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        assert send_response.status_code == 200
        friendship_id = send_response.json()["friendship_id"]
        
        # User2 accepts
        accept_response = api_client.post(f"{base_url}/api/friends/{friendship_id}/accept", headers=user2_auth["headers"])
        assert accept_response.status_code == 200
        
        # User1 removes friend
        response = api_client.delete(f"{base_url}/api/friends/{friendship_id}", headers=user1_auth["headers"])
        print(f"Remove friend status: {response.status_code}")
        print(f"Remove friend response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "removed"
        
        # Verify User2 is no longer in User1's friend list
        friends_response = api_client.get(f"{base_url}/api/friends", headers=user1_auth["headers"])
        assert friends_response.status_code == 200
        friend_ids = [f["user_id"] for f in friends_response.json()["friends"]]
        assert user2_auth["user_id"] not in friend_ids, "User2 should be removed from friend list"
        print("✓ Friend removed successfully")

    def test_cannot_friend_yourself(self, base_url, api_client, user1_auth):
        """Test that user cannot send friend request to themselves"""
        payload = {"target_user_id": user1_auth["user_id"]}
        response = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        print(f"Self-friend request status: {response.status_code}")
        assert response.status_code == 400, "Should not be able to friend yourself"
        print("✓ Self-friend request blocked")

    def test_duplicate_friend_request(self, base_url, api_client, user1_auth, user2_auth):
        """Test that duplicate friend requests are rejected"""
        payload = {"target_user_id": user2_auth["user_id"]}
        # First request
        response1 = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        assert response1.status_code == 200
        
        # Duplicate request
        response2 = api_client.post(f"{base_url}/api/friends/request", json=payload, headers=user1_auth["headers"])
        print(f"Duplicate friend request status: {response2.status_code}")
        assert response2.status_code == 400, "Duplicate friend request should be rejected"
        print("✓ Duplicate friend request blocked")
