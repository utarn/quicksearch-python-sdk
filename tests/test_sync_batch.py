"""
Tests for synchronous batch processing.
"""

import time

import httpx
import pytest
import respx

from quicksearch import (
    BatchIngestOptions,
    BatchIngestResult,
    EventData,
    EventResponse,
    QuickSearchClient,
)


@respx.mock
def test_ingest_events_with_batching_enabled(mock_event_data, mock_api_response):
    """Test batch ingestion with batching enabled returns BatchIngestResult."""
    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=10,
            max_concurrency=3,
        ),
    )

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    events = [EventData(**mock_event_data) for _ in range(10)]
    result = client.ingest_events(events)

    assert isinstance(result, BatchIngestResult)
    assert result.total_count == 10
    assert result.success_count == 10
    assert result.failure_count == 0


@respx.mock
def test_ingest_events_with_batching_disabled(mock_event_data, mock_api_response):
    """Test that batching can be disabled (default behavior)."""
    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(enabled=False),
    )

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    events = [EventData(**mock_event_data) for _ in range(3)]
    responses = client.ingest_events(events)

    # Should return list of EventResponse (backward compatible)
    assert isinstance(responses, list)
    assert len(responses) == 3
    assert all(isinstance(r, EventResponse) for r in responses)


@respx.mock
def test_ingest_events_with_batch_options_override(mock_event_data, mock_api_response):
    """Test per-call batch options override."""
    # Client with batching disabled
    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(enabled=False),
    )

    # Mock the API endpoint
    respx.post("http://localhost:3000/api/events").mock(
        return_value=httpx.Response(201, json=mock_api_response)
    )

    events = [EventData(**mock_event_data) for _ in range(5)]

    # Call with batching enabled via override
    result = client.ingest_events(
        events,
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=10,
            max_concurrency=2,
        ),
    )

    assert isinstance(result, BatchIngestResult)
    assert result.total_count == 5


@respx.mock
def test_ingest_event_batched_queuing(mock_event_data, mock_api_response):
    """Test queuing events with ingest_event_batched."""
    call_count = 0

    def mock_response(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(201, json=mock_api_response)

    respx.post("http://localhost:3000/api/events").mock(side_effect=mock_response)

    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=5,
            flush_interval=1.0,
        ),
    )

    try:
        # Queue events
        for _ in range(3):
            event = EventData(**mock_event_data)
            client.ingest_event_batched(event)

        # Force flush
        client.flush_batch()

        # Give time for flush to complete
        time.sleep(0.5)

        assert call_count == 3
    finally:
        client.close()


@respx.mock
def test_ingest_event_batched_when_disabled(mock_event_data):
    """Test ingest_event_batched raises error when batching is disabled."""
    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(enabled=False),
    )

    event = EventData(**mock_event_data)

    with pytest.raises(RuntimeError, match="Batching is not enabled"):
        client.ingest_event_batched(event)


@respx.mock
def test_batch_processor_auto_flush_on_close(mock_event_data, mock_api_response):
    """Test that batch processor flushes on close."""
    call_count = 0

    def mock_response(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(201, json=mock_api_response)

    respx.post("http://localhost:3000/api/events").mock(side_effect=mock_response)

    with QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=100,  # Large batch size
            flush_interval=60.0,  # Long interval
        ),
    ) as client:
        # Queue a few events (not enough to trigger batch size)
        for _ in range(3):
            event = EventData(**mock_event_data)
            client.ingest_event_batched(event)

        # Events should be flushed on context exit
        assert call_count == 0

    # After close, events should be flushed
    time.sleep(0.5)
    assert call_count == 3


@respx.mock
def test_concurrent_batch_ingestion_with_retries(mock_event_data, mock_api_response):
    """Test concurrent batch ingestion with retry logic."""
    call_count = 0
    fail_count = 0

    def mock_response(request):
        nonlocal call_count, fail_count
        call_count += 1
        # Simulate every 3rd request failing
        if call_count % 3 == 0:
            fail_count += 1
            return httpx.Response(500, json={"statusMessage": "Server error"})
        return httpx.Response(201, json=mock_api_response)

    respx.post("http://localhost:3000/api/events").mock(side_effect=mock_response)

    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=10,
            max_concurrency=3,
            retry_attempts=2,
            retry_delay=0.1,  # Short delay for tests
        ),
    )

    events = [EventData(**mock_event_data) for _ in range(9)]
    result = client.ingest_events(events)

    assert isinstance(result, BatchIngestResult)
    assert result.total_count == 9
    # With retries, some events should succeed
    assert result.success_count >= 6


@respx.mock
def test_batch_ingest_partial_success(mock_event_data, mock_api_response):
    """Test batch ingestion with partial success."""
    def mock_response(request):
        # Fail events with odd index (simulated by checking request body)
        import json

        body = json.loads(request.content)
        event_type = body.get("type", "")
        if "fail" in event_type:
            return httpx.Response(400, json={"statusMessage": "Bad request"})

        return httpx.Response(201, json=mock_api_response)

    respx.post("http://localhost:3000/api/events").mock(side_effect=mock_response)

    client = QuickSearchClient(
        api_key="test-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            max_concurrency=5,
            retry_attempts=0,  # No retries for cleaner test
        ),
    )

    # Create mix of success and failure events
    events = []
    for i in range(10):
        event_data = mock_event_data.copy()
        if i % 2 == 1:
            event_data["type"] = "fail_event"
        events.append(EventData(**event_data))

    result = client.ingest_events(events)

    assert isinstance(result, BatchIngestResult)
    assert result.total_count == 10
    assert result.success_count == 5  # Even indices succeed
    assert result.failure_count == 5  # Odd indices fail
    assert len(result.errors) == 5


def test_batch_ingest_result_success_rate():
    """Test BatchIngestResult success_rate calculation."""
    result = BatchIngestResult(
        success_count=75,
        failure_count=25,
        total_count=100,
    )

    assert result.success_rate == 75.0
