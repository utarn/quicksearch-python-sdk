"""
Asynchronous usage examples for the QuickSearch Python SDK.
"""

import asyncio
from quicksearch import AsyncQuickSearchClient, EventData


async def example_basic_async_usage():
    """Example: Basic async client usage."""
    async with AsyncQuickSearchClient(api_key="your-api-key") as client:
        # Ingest an event
        event = EventData(
            type="user_login",
            application="web_app",
            data={"user_id": "12345"}
        )
        response = await client.ingest_event(event)
        print(f"Event ingested: {response.eventId}")

        # Search for events
        result = await client.search_events(query="login", limit=10)
        print(f"Found {result.count} events")


async def example_concurrent_ingestion():
    """Example: Ingest multiple events concurrently."""
    async with AsyncQuickSearchClient(api_key="your-api-key") as client:
        # Create multiple events
        events = [
            EventData(type=f"event_{i}", data={"index": i})
            for i in range(10)
        ]

        # Ingest all events concurrently
        responses = await client.ingest_events(events)
        print(f"Ingested {len(responses)} events")

        # Print results
        for resp in responses:
            print(f"  - {resp.eventId}: {resp.message}")


async def example_batch_operations():
    """Example: Batch operations with async client."""
    async with AsyncQuickSearchClient(api_key="your-api-key") as client:
        # Batch ingest
        events = [
            EventData(type="click", data={"button": "submit"}),
            EventData(type="view", data={"page": "/home"}),
            EventData(type="error", data={"code": 500}),
        ]

        responses = await client.ingest_events(events)
        print(f"Batch ingest completed: {len(responses)} events")

        # Search with pagination
        for page in range(1, 4):
            result = await client.search_events(
                query="*",
                limit=10,
                timestamp_gte="2024-01-01T00:00:00Z"
            )
            print(f"Page {page}: {result.count} events")


async def example_manual_connection():
    """Example: Manual connect and close."""
    client = AsyncQuickSearchClient(api_key="your-api-key")

    # Manually connect
    await client.connect()

    try:
        # Use the client
        event = EventData(type="test", data={"test": True})
        response = await client.ingest_event(event)
        print(f"Event ingested: {response.success}")
    finally:
        # Always close the connection
        await client.close()


async def example_concurrent_search_and_ingest():
    """Example: Concurrent search and ingest operations."""
    async with AsyncQuickSearchClient(api_key="your-api-key") as client:
        # Run multiple operations concurrently
        ingest_task = client.ingest_event(
            EventData(type="test", data={"concurrent": True})
        )
        search_task = client.search_events(query="login")
        count_task = client.search_events(limit=1)

        # Wait for all to complete
        results = await asyncio.gather(ingest_task, search_task, count_task)

        ingest_response, search_result, count_result = results
        print(f"Ingest: {ingest_response.success}")
        print(f"Search: {search_result.count} events")
        print(f"Count: {count_result.count} events")


async def main():
    """Run all examples."""
    print("=== Async Usage Examples ===\n")

    print("1. Basic async usage:")
    # await example_basic_async_usage()

    print("\n2. Concurrent ingestion:")
    # await example_concurrent_ingestion()

    print("\n3. Batch operations:")
    # await example_batch_operations()

    print("\n4. Manual connection:")
    # await example_manual_connection()

    print("\n5. Concurrent operations:")
    # await example_concurrent_search_and_ingest()


if __name__ == "__main__":
    asyncio.run(main())
