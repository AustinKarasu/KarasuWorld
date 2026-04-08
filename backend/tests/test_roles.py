"""Role management endpoint tests"""
import pytest
import uuid

class TestRoles:
    """Test Discord-like role system with permissions"""

    @pytest.fixture(scope="class")
    def server_owner_auth(self, base_url, api_client):
        """Create user and server for role testing"""
        # Register user
        email = f"TEST_roleowner_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "password": "RolePass123!",
            "username": f"roleowner_{uuid.uuid4().hex[:6]}"
        }
        register_response = api_client.post(f"{base_url}/api/auth/register", json=payload)
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        user_id = register_response.json()["user"]["user_id"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create server
        server_payload = {
            "name": f"TEST_RoleServer_{uuid.uuid4().hex[:6]}",
            "description": "Server for role testing"
        }
        server_response = api_client.post(f"{base_url}/api/servers", json=server_payload, headers=headers)
        assert server_response.status_code == 200
        server_id = server_response.json()["server"]["server_id"]
        
        return {
            "token": token,
            "user_id": user_id,
            "headers": headers,
            "server_id": server_id
        }

    def test_create_role(self, base_url, api_client, server_owner_auth):
        """Test POST /api/servers/:id/roles - create custom role"""
        payload = {
            "name": "Moderator",
            "color": "#3498DB",
            "permissions": 255,  # Some permissions
            "position": 2
        }
        response = api_client.post(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            json=payload,
            headers=server_owner_auth["headers"]
        )
        print(f"Create role status: {response.status_code}")
        print(f"Create role response: {response.text}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "role" in data
        assert data["role"]["name"] == "Moderator"
        assert data["role"]["color"] == "#3498DB"
        assert data["role"]["permissions"] == 255
        assert "role_id" in data["role"]
        print("✓ Role created successfully")
        return data["role"]["role_id"]

    def test_list_roles(self, base_url, api_client, server_owner_auth):
        """Test GET /api/servers/:id/roles - list all roles"""
        # Create a custom role first
        create_payload = {
            "name": "TestRole",
            "color": "#E74C3C",
            "permissions": 128
        }
        create_response = api_client.post(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            json=create_payload,
            headers=server_owner_auth["headers"]
        )
        assert create_response.status_code == 200
        created_role_id = create_response.json()["role"]["role_id"]
        
        # List all roles
        response = api_client.get(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            headers=server_owner_auth["headers"]
        )
        print(f"List roles status: {response.status_code}")
        print(f"List roles response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert isinstance(data["roles"], list)
        # Should have at least @everyone, Admin, and our custom role
        assert len(data["roles"]) >= 3
        role_ids = [r["role_id"] for r in data["roles"]]
        assert created_role_id in role_ids, "Created role should be in list"
        # Check for default roles
        role_names = [r["name"] for r in data["roles"]]
        assert "@everyone" in role_names, "Should have @everyone role"
        assert "Admin" in role_names, "Should have Admin role"
        print(f"✓ Listed {len(data['roles'])} roles")

    def test_update_role(self, base_url, api_client, server_owner_auth):
        """Test PUT /api/servers/:id/roles/:roleId - update role"""
        # Create a role first
        create_payload = {
            "name": "OldName",
            "color": "#000000",
            "permissions": 64
        }
        create_response = api_client.post(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            json=create_payload,
            headers=server_owner_auth["headers"]
        )
        assert create_response.status_code == 200
        role_id = create_response.json()["role"]["role_id"]
        
        # Update the role
        update_payload = {
            "name": "NewName",
            "color": "#FFFFFF",
            "permissions": 512,
            "position": 5
        }
        response = api_client.put(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles/{role_id}",
            json=update_payload,
            headers=server_owner_auth["headers"]
        )
        print(f"Update role status: {response.status_code}")
        print(f"Update role response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "role" in data
        assert data["role"]["name"] == "NewName"
        assert data["role"]["color"] == "#FFFFFF"
        assert data["role"]["permissions"] == 512
        assert data["role"]["position"] == 5
        print("✓ Role updated successfully")

    def test_delete_role(self, base_url, api_client, server_owner_auth):
        """Test DELETE /api/servers/:id/roles/:roleId - delete role"""
        # Create a role first
        create_payload = {
            "name": "ToDelete",
            "color": "#FF0000"
        }
        create_response = api_client.post(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            json=create_payload,
            headers=server_owner_auth["headers"]
        )
        assert create_response.status_code == 200
        role_id = create_response.json()["role"]["role_id"]
        
        # Delete the role
        response = api_client.delete(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles/{role_id}",
            headers=server_owner_auth["headers"]
        )
        print(f"Delete role status: {response.status_code}")
        print(f"Delete role response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        
        # Verify role is no longer in list
        list_response = api_client.get(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            headers=server_owner_auth["headers"]
        )
        assert list_response.status_code == 200
        role_ids = [r["role_id"] for r in list_response.json()["roles"]]
        assert role_id not in role_ids, "Deleted role should not be in list"
        print("✓ Role deleted successfully")

    def test_cannot_delete_default_role(self, base_url, api_client, server_owner_auth):
        """Test that @everyone role cannot be deleted"""
        # Get @everyone role
        list_response = api_client.get(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            headers=server_owner_auth["headers"]
        )
        assert list_response.status_code == 200
        roles = list_response.json()["roles"]
        everyone_role = next((r for r in roles if r["name"] == "@everyone"), None)
        assert everyone_role is not None, "@everyone role should exist"
        
        # Try to delete @everyone role
        response = api_client.delete(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles/{everyone_role['role_id']}",
            headers=server_owner_auth["headers"]
        )
        print(f"Delete default role status: {response.status_code}")
        assert response.status_code == 400, "Should not be able to delete default role"
        print("✓ Default role deletion blocked")

    def test_assign_member_roles(self, base_url, api_client, server_owner_auth):
        """Test PUT /api/servers/:id/members/:userId/roles - assign roles to member"""
        # Create a new user and join the server
        member_email = f"TEST_member_{uuid.uuid4().hex[:8]}@test.com"
        member_payload = {
            "email": member_email,
            "password": "MemberPass123!",
            "username": f"member_{uuid.uuid4().hex[:6]}"
        }
        member_register = api_client.post(f"{base_url}/api/auth/register", json=member_payload)
        assert member_register.status_code == 200
        member_user_id = member_register.json()["user"]["user_id"]
        member_token = member_register.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}
        
        # Get invite code
        invite_response = api_client.get(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/invite",
            headers=server_owner_auth["headers"]
        )
        assert invite_response.status_code == 200
        invite_code = invite_response.json()["invite_code"]
        
        # Member joins server
        join_response = api_client.post(
            f"{base_url}/api/servers/join",
            json={"invite_code": invite_code},
            headers=member_headers
        )
        assert join_response.status_code == 200
        
        # Create a custom role
        role_payload = {
            "name": "Member Role",
            "color": "#00FF00",
            "permissions": 256
        }
        role_response = api_client.post(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            json=role_payload,
            headers=server_owner_auth["headers"]
        )
        assert role_response.status_code == 200
        role_id = role_response.json()["role"]["role_id"]
        
        # Assign role to member
        assign_payload = {"role_ids": [role_id]}
        response = api_client.put(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/members/{member_user_id}/roles",
            json=assign_payload,
            headers=server_owner_auth["headers"]
        )
        print(f"Assign member roles status: {response.status_code}")
        print(f"Assign member roles response: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        
        # Verify member has the role
        members_response = api_client.get(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/members",
            headers=server_owner_auth["headers"]
        )
        assert members_response.status_code == 200
        members = members_response.json()["members"]
        member = next((m for m in members if m["user_id"] == member_user_id), None)
        assert member is not None
        assert role_id in member["role_ids"], "Member should have assigned role"
        print("✓ Member roles assigned successfully")

    def test_role_permissions_check(self, base_url, api_client, server_owner_auth):
        """Test that non-admin cannot manage roles"""
        # Create a regular member
        member_email = f"TEST_norole_{uuid.uuid4().hex[:8]}@test.com"
        member_payload = {
            "email": member_email,
            "password": "NoRolePass123!",
            "username": f"norole_{uuid.uuid4().hex[:6]}"
        }
        member_register = api_client.post(f"{base_url}/api/auth/register", json=member_payload)
        assert member_register.status_code == 200
        member_token = member_register.json()["access_token"]
        member_headers = {"Authorization": f"Bearer {member_token}"}
        
        # Get invite and join
        invite_response = api_client.get(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/invite",
            headers=server_owner_auth["headers"]
        )
        invite_code = invite_response.json()["invite_code"]
        join_response = api_client.post(
            f"{base_url}/api/servers/join",
            json={"invite_code": invite_code},
            headers=member_headers
        )
        assert join_response.status_code == 200
        
        # Try to create role as regular member (should fail)
        role_payload = {
            "name": "Unauthorized Role",
            "color": "#FF0000"
        }
        response = api_client.post(
            f"{base_url}/api/servers/{server_owner_auth['server_id']}/roles",
            json=role_payload,
            headers=member_headers
        )
        print(f"Unauthorized role creation status: {response.status_code}")
        assert response.status_code == 403, "Regular member should not be able to create roles"
        print("✓ Role permission check working")
