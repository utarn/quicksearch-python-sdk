"""
Batch event ingestion examples for the QuickSearch Python SDK.
"""

from quicksearch import (
    AsyncQuickSearchClient,
    BatchIngestOptions,
    BatchIngestResult,
    EventData,
    QuickSearchClient,
)


def example_batch_ingest_client_level():
    """Example: Enable batching at client level."""
    # Create client with batching enabled
    client = QuickSearchClient(
        base_url="http://localhost:3000",
        api_key="your-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=100,
            flush_interval=2.0,
            max_concurrency=5,
        ),
    )

    try:
        # Create events
        events = [
            EventData(
                type="user_action",
                application="web_app",
                data={"action": "click", "user_id": i},
            )
            for i in range(1000)
        ]

        # Ingest with batching - returns BatchIngestResult
        result: BatchIngestResult = client.ingest_events(events)

        print(f"Total events: {result.total_count}")
        print(f"Success: {result.success_count}")
        print(f"Failed: {result.failure_count}")
        print(f"Success rate: {result.success_rate:.1f}%")
        print(f"Processing time: {result.processing_time_ms}ms")

        if result.errors:
            print(f"First error: {result.errors[0].error_message}")
    finally:
        client.close()


def example_batch_ingest_per_call():
    """Example: Enable batching per API call."""
    # Create client with batching disabled (default)
    client = QuickSearchClient(api_key="your-api-key")

    try:
        events = [EventData(type="metric", data={"value": i}) for i in range(500)]

        # Enable batching for this call only
        result: BatchIngestResult = client.ingest_events(
            events,
            batch_options=BatchIngestOptions(
                enabled=True,
                batch_size=50,
                max_concurrency=10,
            ),
        )

        print(f"Ingested {result.success_count} events")
    finally:
        client.close()


def example_streaming_events():
    """Example: Stream events with automatic batching."""
    client = QuickSearchClient(
        api_key="your-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=100,
            flush_interval=1.0,
        ),
    )

    try:
        # Queue many events non-blocking
        for i in range(10000):
            event = EventData(
                type="metric",
                application="monitor",
                data={"cpu_usage": i % 100},
            )
            client.ingest_event_batched(event)

            if i % 1000 == 0:
                print(f"Queued {i} events")

        # Flush any remaining events
        client.flush_batch()
        print("All events flushed")
    finally:
        client.close()


def example_custom_retry_logic():
    """Example: Custom retry configuration."""
    client = QuickSearchClient(
        api_key="your-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            retry_attempts=5,  # More retries
            retry_delay=2.0,  # Longer initial delay (seconds)
            max_concurrency=3,  # Less concurrency for retries
        ),
    )

    try:
        events = [EventData(type="test", data={"index": i}) for i in range(100)]

        result = client.ingest_events(events)
        print(f"Success: {result.success_count}/{result.total_count}")

        # Check errors
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"  - Event {error.event_index}: {error.error_message}")
    finally:
        client.close()


async def example_async_batch_ingest():
    """Example: Async batch ingestion."""
    async with AsyncQuickSearchClient(
        api_key="your-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=50,
            max_concurrency=10,
        ),
    ) as client:
        events = [
            EventData(
                type="async_event",
                data={"timestamp": i},
            )
            for i in range(500)
        ]

        result: BatchIngestResult = await client.ingest_events(events)

        print(f"Async ingest: {result.success_count}/{result.total_count}")
        print(f"Processing time: {result.processing_time_ms}ms")


async def example_async_streaming():
    """Example: Async streaming with automatic batching."""
    async with AsyncQuickSearchClient(
        api_key="your-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=100,
            flush_interval=2.0,
        ),
    ) as client:
        # Queue events asynchronously
        for i in range(5000):
            event = EventData(
                type="log_entry",
                data={"line": f"Log line {i}"},
            )
            await client.ingest_event_batched(event)

        # Force flush
        await client.flush_batch()
        print("All async events flushed")


def example_backward_compatibility():
    """Example: Existing code continues to work without changes."""
    client = QuickSearchClient(api_key="your-api-key")

    try:
        events = [
            EventData(type="old_style", data={"id": i})
            for i in range(10)
        ]

        # Returns list of EventResponse (backward compatible)
        responses = client.ingest_events(events)

        print(f"Ingested {len(responses)} events")
        for resp in responses:
            print(f"  - {resp.eventId}: {resp.success}")
    finally:
        client.close()


def example_high_load_batching():
    """Example: High-load batch ingestion under stress."""
    client = QuickSearchClient(
        api_key="your-api-key",
        batch_options=BatchIngestOptions(
            enabled=True,
            batch_size=50,
            flush_interval=0.5,
            max_concurrency=10,
            retry_attempts=3,
        ),
    )

    try:
        # Generate large number of events
        events = [
            EventData(
                type="load_test",
                application="test_app",
                data={"index": i},
            )
            for i in range(5000)
        ]

        result = client.ingest_events(events)

        print(f"Load test results:")
        print(f"  Total: {result.total_count}")
        print(f"  Success: {result.success_count}")
        print(f"  Failed: {result.failure_count}")
        print(f"  Rate: {result.success_rate:.2f}%")
        print(f"  Time: {result.processing_time_ms}ms")
    finally:
        client.close()


if __name__ == "__main__":
    import asyncio

    print("=== Batch Ingestion Examples ===\n")

    print("1. Client-level batching:")
    # example_batch_ingest_client_level()

    print("\n2. Per-call batching:")
    # example_batch_ingest_per_call()

    print("\n3. Streaming events:")
    # example_streaming_events()

    print("\n4. Custom retry logic:")
    # example_custom_retry_logic()

    print("\n5. Async batch ingestion:")
    # asyncio.run(example_async_batch_ingest())

    print("\n6. Async streaming:")
    # asyncio.run(example_async_streaming())

    print("\n7. Backward compatibility:")
    # example_backward_compatibility()

    print("\n8. High load batching:")
    # example_high_load_batching()
