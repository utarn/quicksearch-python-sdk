"""
Tests for Pydantic models.
"""

import pytest

from quicksearch.models import EventData, SyslogData, EventResponse, EventSearchResult


class TestEventData:
    """Tests for EventData model."""

    def test_create_event_with_required_fields(self):
        """Test creating event with only required fields."""
        event = EventData(type="user_login")
        assert event.type == "user_login"
        assert event.application is None
        assert event.message is None
        assert event.data == {}

    def test_create_event_with_all_fields(self):
        """Test creating event with all fields."""
        event = EventData(
            type="user_login",
            application="web_app",
            timestamp="2024-01-01T00:00:00Z",
            message="User logged in",
            data={"user_id": "12345"},
        )
        assert event.type == "user_login"
        assert event.application == "web_app"
        assert event.timestamp == "2024-01-01T00:00:00Z"
        assert event.message == "User logged in"
        assert event.data == {"user_id": "12345"}

    def test_event_data_to_dict(self):
        """Test converting event data to dictionary."""
        event = EventData(type="test", data={"key": "value"})
        data = event.model_dump(exclude_none=True)
        assert data["type"] == "test"
        assert data["data"] == {"key": "value"}

    def test_invalid_timestamp(self):
        """Test validation of invalid timestamp format."""
        with pytest.raises(ValueError, match="timestamp must be in ISO 8601 format"):
            EventData(type="test", timestamp="invalid-timestamp")

    def test_valid_timestamp_formats(self):
        """Test various valid ISO 8601 timestamp formats."""
        valid_timestamps = [
            "2024-01-01T00:00:00Z",
            "2024-01-01T00:00:00.123Z",
            "2024-01-01T00:00:00+00:00",
            "2024-01-01T00:00:00.123+00:00",
        ]
        for ts in valid_timestamps:
            event = EventData(type="test", timestamp=ts)
            assert event.timestamp == ts


class TestSyslogData:
    """Tests for SyslogData model."""

    def test_create_syslog_with_all_fields(self):
        """Test creating syslog with all fields."""
        syslog = SyslogData(
            type="auth_failure",
            severity="error",
            hostname="web-server-01",
            message="Authentication failed",
            data={"user": "admin"},
        )
        assert syslog.type == "auth_failure"
        assert syslog.severity == "error"
        assert syslog.hostname == "web-server-01"
        assert syslog.message == "Authentication failed"
        assert syslog.data == {"user": "admin"}

    def test_create_syslog_minimal(self):
        """Test creating syslog with minimal fields."""
        syslog = SyslogData()
        assert syslog.type is None
        assert syslog.severity is None
        assert syslog.data == {}


class TestEventResponse:
    """Tests for EventResponse model."""

    def test_create_response_with_event_id(self):
        """Test creating response with event ID."""
        response = EventResponse(
            success=True,
            message="Event logged successfully",
            eventId="1704067200000-abc123",
        )
        assert response.success is True
        assert response.message == "Event logged successfully"
        assert response.eventId == "1704067200000-abc123"

    def test_create_response_without_event_id(self):
        """Test creating response without event ID."""
        response = EventResponse(success=True, message="OK")
        assert response.success is True
        assert response.eventId is None


class TestEventSearchResult:
    """Tests for EventSearchResult model."""

    def test_create_search_result(self):
        """Test creating search result."""
        result = EventSearchResult(
            success=True,
            events=[{"id": "1", "type": "test"}],
            count=1,
            estimated_total=100,
            processing_time_ms=12,
            query="test",
        )
        assert result.success is True
        assert result.count == 1
        assert result.estimated_total == 100
        assert result.processing_time_ms == 12
        assert result.query == "test"
        assert len(result.events) == 1

    def test_create_search_result_minimal(self):
        """Test creating minimal search result."""
        result = EventSearchResult(
            success=True,
            events=[],
            count=0,
        )
        assert result.success is True
        assert result.count == 0
        assert result.estimated_total is None
        assert result.processing_time_ms is None
        assert result.query is None
