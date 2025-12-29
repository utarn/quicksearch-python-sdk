"""
Tests for the asynchronous QuickSearch client.
"""

import httpx
import pytest
import respx

from quicksearch import (
    AsyncQuickSearchClient,
    AuthenticationError,
    EventData,
    EventResponse,
    EventSearchResult,
    SyslogData,
    ValidationError,
)


@respx.mock
async def test_async_ingest_event_success(mock_event_data, mock_api_response):
    """Test successful async event ingestion."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        # Mock the API endpoint
        route = respx.post("http://localhost:3000/api/events").mock(
            return_value=httpx.Response(201, json=mock_api_response)
        )

        # Test with EventData model
        event = EventData(**mock_event_data)
        response = await client.ingest_event(event)

        assert response.success is True
        assert response.eventId == "1704067200000-abc123"
        assert route.called


@respx.mock
async def test_async_ingest_event_with_dict(mock_event_data, mock_api_response):
    """Test async event ingestion with dictionary input."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        # Mock the API endpoint
        respx.post("http://localhost:3000/api/events").mock(
            return_value=httpx.Response(201, json=mock_api_response)
        )

        # Test with dictionary
        response = await client.ingest_event(mock_event_data)

        assert response.success is True
        assert response.eventId == "1704067200000-abc123"


@respx.mock
async def test_async_ingest_event_validation_error(mock_event_data):
    """Test async event validation error handling."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        # Mock the API endpoint to return 400
        respx.post("http://localhost:3000/api/events").mock(
            return_value=httpx.Response(
                400,
                json={"statusMessage": "Event type is required"},
            )
        )

        with pytest.raises(ValidationError, match="Event type is required"):
            await client.ingest_event(mock_event_data)


@respx.mock
async def test_async_search_events(mock_search_response):
    """Test async event search."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        # Mock the API endpoint
        respx.get("http://localhost:3000/api/events").mock(
            return_value=httpx.Response(200, json=mock_search_response)
        )

        result = await client.search_events(query="user_login", limit=10)

        assert result.success is True
        assert result.count == 1
        assert len(result.events) == 1
        assert result.events[0]["type"] == "user_login"


@respx.mock
async def test_async_ingest_syslog(mock_syslog_data, mock_api_response):
    """Test async syslog ingestion."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        # Mock the API endpoint
        respx.post("http://localhost:3000/api/syslog").mock(
            return_value=httpx.Response(201, json=mock_api_response)
        )

        syslog = SyslogData(**mock_syslog_data)
        response = await client.ingest_syslog(syslog)

        assert response.success is True
        assert response.eventId == "1704067200000-abc123"


@respx.mock
async def test_async_ingest_events_batch(mock_event_data, mock_api_response):
    """Test async batch event ingestion."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        # Mock the API endpoint
        respx.post("http://localhost:3000/api/events").mock(
            return_value=httpx.Response(201, json=mock_api_response)
        )

        events = [EventData(**mock_event_data) for _ in range(3)]
        responses = await client.ingest_events(events)

        assert len(responses) == 3
        assert all(r.success for r in responses)


async def test_async_context_manager():
    """Test async client as context manager."""
    async with AsyncQuickSearchClient(api_key="test-api-key") as client:
        assert client is not None
        assert client.auth.api_key == "test-api-key"
    # Client should be closed after exiting context


async def test_async_connect_close():
    """Test manual connect and close."""
    client = AsyncQuickSearchClient(api_key="test-api-key")
    await client.connect()
    assert client._client is not None
    await client.close()
    assert client._client is None


async def test_async_not_connected_error():
    """Test error when using client without connecting."""
    client = AsyncQuickSearchClient(api_key="test-api-key")

    with pytest.raises(RuntimeError, match="Client not connected"):
        await client.search_events()
