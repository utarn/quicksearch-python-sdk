"""
Error handling examples for the QuickSearch Python SDK.
"""

from quicksearch import (
    QuickSearchClient,
    EventData,
    AuthenticationError,
    PermissionError,
    ValidationError,
    RateLimitError,
    ServerError,
    ConnectionError,
    QuickSearchError,
)


def example_comprehensive_error_handling():
    """Example: Comprehensive error handling."""
    client = QuickSearchClient(api_key="your-api-key")

    try:
        event = EventData(type="test", data={"test": True})
        response = client.ingest_event(event)
        print(f"Success: {response.success}")
    except AuthenticationError:
        print("Error: Invalid API key or authentication failed")
    except PermissionError:
        print("Error: API key lacks required permission")
    except ValidationError as e:
        print(f"Error: Invalid data - {e}")
    except RateLimitError:
        print("Error: Daily API rate limit exceeded")
    except ServerError:
        print("Error: Server error occurred")
    except ConnectionError:
        print("Error: Failed to connect to server")
    except QuickSearchError as e:
        print(f"Error: {e}")
    finally:
        client.close()


def example_specific_error_handling():
    """Example: Handle specific errors differently."""
    client = QuickSearchClient(api_key="your-api-key")

    try:
        # Attempt to ingest event
        event = EventData(type="test", data={"test": True})
        response = client.ingest_event(event)
        print(f"Event ingested: {response.eventId}")
    except AuthenticationError:
        # Handle authentication - maybe prompt for new credentials
        print("Authentication failed. Please check your API key.")
    except PermissionError as e:
        # Handle permission errors
        print(f"Permission denied: {e}")
        print("You may need to update your API key permissions.")
    except RateLimitError:
        # Handle rate limiting - maybe wait and retry
        print("Rate limit exceeded. Please wait before retrying.")
    except ValidationError as e:
        # Handle validation errors - fix the data
        print(f"Validation error: {e}")
        print("Please check your event data.")
    except (ServerError, ConnectionError) as e:
        # Handle server/connection errors
        print(f"Connection/server error: {e}")
        print("Please check your connection and try again.")

    client.close()


def example_retry_on_rate_limit():
    """Example: Retry logic on rate limit."""
    import time

    client = QuickSearchClient(api_key="your-api-key")
    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            event = EventData(type="test", data={"test": True})
            response = client.ingest_event(event)
            print(f"Success on attempt {attempt + 1}")
            break
        except RateLimitError:
            if attempt < max_retries - 1:
                print(f"Rate limit hit. Waiting {retry_delay}s before retry...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Giving up.")
        except QuickSearchError as e:
            print(f"Non-retryable error: {e}")
            break

    client.close()


def example_validation_error_handling():
    """Example: Handle validation errors specifically."""
    client = QuickSearchClient(api_key="your-api-key")

    try:
        # Try to create event with invalid timestamp
        event = EventData(
            type="test",
            timestamp="invalid-timestamp-format"
        )
        response = client.ingest_event(event)
    except ValidationError as e:
        print(f"Validation failed: {e}")
        # Fix the timestamp and retry
        from datetime import datetime, timezone

        event = EventData(
            type="test",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        response = client.ingest_event(event)
        print(f"Success with corrected data: {response.success}")

    client.close()


def example_context_manager_with_error_handling():
    """Example: Using context manager with error handling."""
    try:
        with QuickSearchClient(api_key="your-api-key") as client:
            event = EventData(type="test", data={"test": True})
            response = client.ingest_event(event)
            print(f"Success: {response.success}")
    except AuthenticationError:
        print("Authentication failed")
    except PermissionError:
        print("Permission denied")
    except QuickSearchError as e:
        print(f"Error: {e}")


def example_search_with_error_handling():
    """Example: Error handling for search operations."""
    client = QuickSearchClient(api_key="your-api-key")

    try:
        result = client.search_events(
            query="error",
            limit=10,
            source="api"
        )
        print(f"Found {result.count} events")

        # Process events with error handling
        for event in result.events:
            try:
                print(f"Event: {event['type']} - {event.get('message', 'No message')}")
            except KeyError as e:
                print(f"Error processing event: {e}")

    except ValidationError as e:
        print(f"Invalid search parameters: {e}")
    except AuthenticationError:
        print("Authentication failed for search")
    except QuickSearchError as e:
        print(f"Search error: {e}")

    client.close()


if __name__ == "__main__":
    print("=== Error Handling Examples ===\n")

    print("1. Comprehensive error handling:")
    # example_comprehensive_error_handling()

    print("\n2. Specific error handling:")
    # example_specific_error_handling()

    print("\n3. Retry on rate limit:")
    # example_retry_on_rate_limit()

    print("\n4. Validation error handling:")
    # example_validation_error_handling()

    print("\n5. Context manager with error handling:")
    # example_context_manager_with_error_handling()

    print("\n6. Search with error handling:")
    # example_search_with_error_handling()
