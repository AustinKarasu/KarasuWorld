import pytest
import requests
import os

@pytest.fixture(scope="session")
def base_url():
    """Get base URL from environment"""
    url = os.environ.get('EXPO_PUBLIC_BACKEND_URL')
    if not url:
        pytest.fail("EXPO_PUBLIC_BACKEND_URL not set in environment")
    return url.rstrip('/')

@pytest.fixture(scope="session")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session

@pytest.fixture(scope="session")
def admin_credentials():
    """Admin credentials from test_credentials.md"""
    return {
        "email": "admin@karasuworld.com",
        "password": "KarasuAdmin123!"
    }

@pytest.fixture(scope="session")
def test_user_credentials():
    """Test user credentials"""
    return {
        "email": "testuser@test.com",
        "password": "Test123!"
    }
