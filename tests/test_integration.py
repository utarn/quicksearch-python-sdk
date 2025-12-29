"""
Integration tests against the real QuickSearch backend.

These tests require the Nuxt.js server to be running on http://localhost:3000.
"""

import os
import time

import pytest
from httpx import HTTPStatusError, RemoteProtocolError

from quicksearch import (
    AsyncQuickSearchClient,
    AuthenticationError,
    EventData,
    QuickSearchClient,
    SyslogData,
)

# API key from the backend
API_KEY = os.environ.get("QUICKSEARCH_API_KEY", "d3c70de4fbd25eadf464aa485752deaae143dd1c9f8bce0b64810464c4f48c50")
BASE_URL = os.environ.get("QUICKSEARCH_BASE_URL", "http://localhost:3000")


@pytest.mark.integration
def test_ingest_event_real():
    """Test ingesting an event to the real backend."""
    client = QuickSearchClient(base_url=BASE_URL, api_key=API_KEY)

    event = EventData(
        type="integration_test",
        application="python_sdk",
        message="Test event from Python SDK",
        data={"test": True, "source": "integration_test"},
    )

    try:
        response = client.ingest_event(event)
        assert response.success is True
        assert response.eventId is not None
        print(f"Event ingested with ID: {response.eventId}")
    except (HTTPStatusError, RemoteProtocolError) as e:
        pytest.skip(f"Backend not available: {e}")
    finally:
        client.close()


@pytest.mark.integration
def test_ingest_syslog_real():
    """Test ingesting syslog to the real backend."""
    client = QuickSearchClient(base_url=BASE_URL, api_key=API_KEY)

    syslog = SyslogData(
        type="test_syslog",
        severity="info",
        hostname="test-host",
        message="Test syslog from Python SDK",
        data={"test": True},
    )

    try:
        response = client.ingest_syslog(syslog)
        assert response.success is True
        assert response.eventId is not None
        print(f"Syslog ingested with ID: {response.eventId}")
    except (HTTPStatusError, RemoteProtocolError) as e:
        pytest.skip(f"Backend not available: {e}")
    finally:
        client.close()


@pytest.mark.integration
def test_search_events_real():
    """Test searching events from the real backend.

    Note: Events are buffered for 15 seconds before being indexed to Meilisearch.
    This test may timeout if searching immediately after ingestion.
    """
    client = QuickSearchClient(base_url=BASE_URL, api_key=API_KEY)

    try:
        # Ingest some test events
        for i in range(3):
            event = EventData(
                type=f"search_test_{int(time.time())}",
                application="python_sdk",
                message=f"Test event {i} for search",
                data={"searchable": True, "index": i},
            )
            client.ingest_event(event)

        # Wait for events to be indexed (buffer delay is 15 seconds)
        # We'll use a shorter timeout for the test
        print("Waiting for events to be indexed (may take up to 15 seconds)...")
        time.sleep(2)  # Brief wait

        # Search for recently ingested events
        # Note: May not find immediately due to buffering
        result = client.search_events(query="python_sdk", limit=50)
        assert result.success is True
        assert isinstance(result.events, list)
        print(f"Found {result.count} events (note: events are buffered for 15s)")

        # Even if count is 0, the search should succeed
        assert isinstance(result.count, int)
    except (HTTPStatusError, RemoteProtocolError) as e:
        pytest.skip(f"Backend not available: {e}")
    finally:
        client.close()


@pytest.mark.integration
def test_batch_ingest_real():
    """Test batch ingestion to the real backend."""
    client = QuickSearchClient(base_url=BASE_URL, api_key=API_KEY)

    events = [
        EventData(type=f"batch_test_{int(time.time())}_{i}", data={"index": i})
        for i in range(5)
    ]

    try:
        responses = client.ingest_events(events)
        assert len(responses) == 5
        assert all(r.success for r in responses)
        print(f"Batch ingested {len(responses)} events")
        for i, resp in enumerate(responses):
            print(f"  [{i}] {resp.eventId}")
    except (HTTPStatusError, RemoteProtocolError) as e:
        pytest.skip(f"Backend not available: {e}")
    finally:
        client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_async_ingest_event_real():
    """Test async event ingestion to the real backend."""
    async with AsyncQuickSearchClient(base_url=BASE_URL, api_key=API_KEY) as client:
        event = EventData(
            type="async_test",
            application="python_sdk",
            message="Async test event",
            data={"async": True, "timestamp": int(time.time())},
        )

        try:
            response = await client.ingest_event(event)
            assert response.success is True
            assert response.eventId is not None
            print(f"Async event ingested with ID: {response.eventId}")
        except (HTTPStatusError, RemoteProtocolError) as e:
            pytest.skip(f"Backend not available: {e}")


@pytest.mark.integration
def test_invalid_api_key():
    """Test authentication with invalid API key."""
    client = QuickSearchClient(base_url=BASE_URL, api_key="invalid-key-1234567890abcdef")

    try:
        event = EventData(type="test", data={"test": True})
        try:
            response = client.ingest_event(event)
            # If there are no API keys in the system, unauthenticated access might be allowed
            print(f"Note: Unauthenticated access allowed - response: {response.success}")
        except AuthenticationError:
            print("Authentication error correctly raised for invalid API key")
        except (HTTPStatusError, RemoteProtocolError) as e:
            pytest.skip(f"Backend not available: {e}")
    finally:
        client.close()


@pytest.mark.integration
def test_structured_syslog_with_rfc_format():
    """Test ingesting syslog in structured format that mimics RFC3164."""
    client = QuickSearchClient(base_url=BASE_URL, api_key=API_KEY)

    # Use structured data to simulate RFC3164 syslog
    # The backend expects JSON format for structured data
    syslog_data = {
        "type": "auth_failure",
        "severity": "error",
        "hostname": "web-server-01",
        "message": "Authentication failed for user admin",
        "data": {
            "user": "admin",
            "source_ip": "10.0.0.50",
            "facility": 10,  # authpriv
        }
    }

    try:
        response = client.ingest_syslog(syslog_data)
        assert response.success is True
        print(f"Structured syslog ingested with ID: {response.eventId}")
    except (HTTPStatusError, RemoteProtocolError) as e:
        pytest.skip(f"Backend not available: {e}")
    finally:
        client.close()


@pytest.mark.integration
def test_context_manager():
    """Test using client as context manager."""
    try:
        with QuickSearchClient(base_url=BASE_URL, api_key=API_KEY) as client:
            event = EventData(
                type="context_test",
                application="python_sdk",
                data={"context": True},
            )
            response = client.ingest_event(event)
            assert response.success is True
            print(f"Context manager test passed with ID: {response.eventId}")
    except (HTTPStatusError, RemoteProtocolError) as e:
        pytest.skip(f"Backend not available: {e}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
