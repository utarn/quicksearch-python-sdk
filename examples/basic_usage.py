"""
Basic usage examples for the QuickSearch Python SDK.
"""

from quicksearch import QuickSearchClient, EventData, SyslogData


def example_ingest_single_event():
    """Example: Ingest a single event."""
    client = QuickSearchClient(
        base_url="http://localhost:3000",
        api_key="your-api-key-here"
    )

    # Create an event
    event = EventData(
        type="user_login",
        application="web_app",
        message="User logged in successfully",
        data={
            "user_id": "12345",
            "username": "john_doe",
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
        }
    )

    # Ingest the event
    response = client.ingest_event(event)
    print(f"Event ingested: {response.success}")
    print(f"Event ID: {response.eventId}")

    # Cleanup
    client.close()


def example_ingest_multiple_events():
    """Example: Ingest multiple events in batch."""
    client = QuickSearchClient(api_key="your-api-key")

    # Create multiple events
    events = [
        EventData(type="click", data={"button": "submit", "page": "/checkout"}),
        EventData(type="view", data={"page": "/home", "duration": 5.2}),
        EventData(type="error", data={"code": 500, "message": "Internal error"}),
    ]

    # Ingest all events
    responses = client.ingest_events(events)
    print(f"Ingested {len(responses)} events")
    for resp in responses:
        print(f"  - {resp.eventId}: {resp.message}")

    client.close()


def example_search_events():
    """Example: Search for events."""
    client = QuickSearchClient(api_key="your-api-key")

    # Simple search
    result = client.search_events(query="login", limit=10)
    print(f"Found {result.count} events for 'login'")
    for event in result.events:
        print(f"  - {event.get('timestamp_iso')}: {event.get('message')}")

    # Search with filters
    result = client.search_events(
        query="error",
        source="api",
        severity="critical",
        limit=50
    )
    print(f"Found {result.count} critical errors from API")

    client.close()


def example_using_context_manager():
    """Example: Using client as context manager."""
    with QuickSearchClient(api_key="your-api-key") as client:
        # Ingest event
        event = EventData(type="test_event", data={"test": True})
        response = client.ingest_event(event)
        print(f"Success: {response.success}")

        # Search
        result = client.search_events(query="test_event")
        print(f"Found {result.count} test events")

    # Session is automatically closed


def example_ingest_syslog():
    """Example: Ingest syslog messages."""
    client = QuickSearchClient(api_key="your-api-key")

    # Structured syslog
    syslog = SyslogData(
        type="auth_failure",
        severity="error",
        hostname="web-server-01",
        message="Authentication failed for user admin",
        data={
            "user": "admin",
            "source_ip": "10.0.0.50",
            "attempt_count": 3,
        }
    )

    response = client.ingest_syslog(syslog)
    print(f"Syslog ingested: {response.success}")

    # Raw syslog string (RFC3164 format)
    raw_syslog = "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for user"
    response = client.ingest_syslog(raw_syslog)
    print(f"Raw syslog ingested: {response.success}")

    client.close()


def example_with_dictionary():
    """Example: Using dictionaries instead of models."""
    client = QuickSearchClient(api_key="your-api-key")

    # Pass dictionary directly
    event_dict = {
        "type": "user_action",
        "application": "mobile_app",
        "message": "User clicked button",
        "data": {"action": "click", "element": "submit_button"},
    }

    response = client.ingest_event(event_dict)
    print(f"Event ingested: {response.success}")

    client.close()


if __name__ == "__main__":
    print("=== Basic Usage Examples ===\n")

    print("1. Ingest single event:")
    # example_ingest_single_event()

    print("\n2. Ingest multiple events:")
    # example_ingest_multiple_events()

    print("\n3. Search events:")
    # example_search_events()

    print("\n4. Using context manager:")
    # example_using_context_manager()

    print("\n5. Ingest syslog:")
    # example_ingest_syslog()

    print("\n6. Using dictionaries:")
    # example_with_dictionary()
