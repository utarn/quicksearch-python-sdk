"""
Tests for the synchronous QuickSearch client.
"""

import json

import httpx
import pytest
import respx

from quicksearch import (
    AuthenticationError,
    EventData,
    EventResponse,
    EventSearchResult,
    QuickSearchClient,
    QuickSearchError,
    SyslogData,
    ValidationError,
)


@respx.mock
def test_ingest_event_success(mock_event_data, mock_api_response):
    """Test successful event ingestion."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    route = respx.post(
        "http://localhost:3000/api/events",
        params={"api_key": "test-api-key"},
    ).mock(return_value=httpx.Response(201, json=mock_api_response))

    # Test with EventData model
    event = EventData(**mock_event_data)
    response = client.ingest_event(event)

    assert response.success is True
    assert response.eventId == "1704067200000-abc123"
    assert route.called


@respx.mock
def test_ingest_event_with_dict(mock_event_data, mock_api_response):
    """Test event ingestion with dictionary input."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    # Test with dictionary
    response = client.ingest_event(mock_event_data)

    assert response.success is True
    assert response.eventId == "1704067200000-abc123"


@respx.mock
def test_ingest_event_validation_error(mock_event_data):
    """Test event validation error handling."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint to return 400
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(
            400,
            json={"statusMessage": "Event type is required"},
        )
    )

    with pytest.raises(ValidationError, match="Event type is required"):
        client.ingest_event(mock_event_data)


@respx.mock
def test_ingest_event_authentication_error(mock_event_data):
    """Test authentication error handling."""
    client = QuickSearchClient(api_key="invalid-key")

    # Mock the API endpoint to return 401
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(
            401,
            json={"statusMessage": "Invalid API key"},
        )
    )

    with pytest.raises(AuthenticationError, match="Invalid API key"):
        client.ingest_event(mock_event_data)


@respx.mock
def test_search_events(mock_search_response):
    """Test event search."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    respx.get("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(200, json=mock_search_response)
    )

    result = client.search_events(query="user_login", limit=10)

    assert result.success is True
    assert result.count == 1
    assert result.estimated_total == 1
    assert len(result.events) == 1
    assert result.events[0]["type"] == "user_login"


@respx.mock
def test_search_events_with_filters(mock_search_response):
    """Test event search with filters."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    route = respx.get("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(200, json=mock_search_response)
    )

    result = client.search_events(
        query="error",
        source="syslog",
        severity="critical",
        limit=50,
    )

    assert result.success is True
    # Verify the request was made with the correct params
    assert route.called


@respx.mock
def test_ingest_syslog_structured(mock_syslog_data, mock_api_response):
    """Test syslog ingestion with structured data."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/syslog").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    # Test with SyslogData model
    syslog = SyslogData(**mock_syslog_data)
    response = client.ingest_syslog(syslog)

    assert response.success is True
    assert response.eventId == "1704067200000-abc123"


@respx.mock
def test_ingest_syslog_raw_string(mock_api_response):
    """Test syslog ingestion with raw string."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/syslog").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    # Test with raw syslog string
    raw_syslog = "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for user"
    response = client.ingest_syslog(raw_syslog)

    assert response.success is True


@respx.mock
def test_ingest_events_batch(mock_event_data, mock_api_response):
    """Test batch event ingestion."""
    client = QuickSearchClient(api_key="test-api-key")

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    events = [EventData(**mock_event_data) for _ in range(3)]
    responses = client.ingest_events(events)

    assert len(responses) == 3
    assert all(r.success for r in responses)


def test_context_manager():
    """Test client as context manager."""
    with QuickSearchClient(api_key="test-api-key") as client:
        assert client is not None
        assert client.auth.api_key == "test-api-key"
    # Session should be closed after exiting context


def test_close():
    """Test closing the client."""
    client = QuickSearchClient(api_key="test-api-key")
    client.close()
    # Should not raise any exception
