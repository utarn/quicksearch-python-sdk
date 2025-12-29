"""
Pytest configuration and fixtures for testing.
"""

import pytest

# Mock event data fixtures
@pytest.fixture
def mock_event_data():
    """Mock event data for testing."""
    return {
        "type": "user_login",
        "application": "web_app",
        "message": "User logged in successfully",
        "data": {"user_id": "12345", "ip_address": "192.168.1.100"},
    }


@pytest.fixture
def mock_syslog_data():
    """Mock syslog data for testing."""
    return {
        "type": "auth_failure",
        "severity": "error",
        "hostname": "web-server-01",
        "message": "Authentication failed for user admin",
        "data": {"user": "admin", "source_ip": "10.0.0.50"},
    }


@pytest.fixture
def mock_api_response():
    """Mock API response for testing."""
    return {
        "success": True,
        "message": "Event logged successfully",
        "eventId": "1704067200000-abc123",
    }


@pytest.fixture
def mock_search_response():
    """Mock search response for testing."""
    return {
        "success": True,
        "events": [
            {
                "id": "1704067200000-abc123",
                "timestamp": 1704067200,
                "timestamp_iso": "2024-01-01T00:00:00Z",
                "type": "user_login",
                "source": "api",
                "application": "web_app",
                "message": "User logged in successfully",
            }
        ],
        "count": 1,
        "estimated_total": 1,
        "processing_time_ms": 12,
        "query": "user_login",
    }
