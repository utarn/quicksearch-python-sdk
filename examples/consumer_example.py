"""
Example: How another Python project uses the QuickSearch SDK.

This shows how to set up a consuming project.
"""

# ============================================================
# SETUP (in your consuming project's pyproject.toml):
# ============================================================

# For LOCAL development (editable install):
# [project.dependencies]
# quicksearch-python-sdk = {path = "/Users/utarn/projects/quick-search/lib/python", editable = true}

# For PRODUCTION (after publishing to PyPI):
# [project.dependencies]
# quicksearch-python-sdk = ">=0.1.0"

# ============================================================
# USAGE IN YOUR CODE:
# ============================================================

import asyncio
import logging
from datetime import datetime

from quicksearch import (
    AsyncQuickSearchClient,
    EventData,
    QuickSearchClient,
    QuickSearchError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
QUICKSEARCH_URL = "http://localhost:3000"  # Or your production URL
API_KEY = "2cbe41dfe1ac71ba836be43a5fcf7eaa2b5071a0ac194847f284e24e9a71fd01"


class MyAppLogger:
    """Example class that logs events to QuickSearch."""

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.client = QuickSearchClient(
            base_url=QUICKSEARCH_URL,
            api_key=API_KEY,
        )

    def log_user_action(self, user_id: str, action: str, **metadata):
        """Log a user action event."""
        event = EventData(
            type="user_action",
            application=self.app_name,
            message=f"User {user_id} performed {action}",
            data={
                "user_id": user_id,
                "action": action,
                **metadata,
            },
        )

        try:
            response = self.client.ingest_event(event)
            logger.info(f"Event logged: {response.eventId}")
            return response.eventId
        except QuickSearchError as e:
            logger.error(f"Failed to log event: {e}")
            return None

    def log_error(self, error: Exception, context: dict | None = None):
        """Log an error event."""
        event = EventData(
            type="error",
            application=self.app_name,
            message=str(error),
            data={
                "error_type": type(error).__name__,
                "context": context or {},
            },
        )

        try:
            response = self.client.ingest_event(event)
            logger.info(f"Error logged: {response.eventId}")
        except QuickSearchError as e:
            logger.error(f"Failed to log error: {e}")

    def search_recent_errors(self, limit: int = 10):
        """Search for recent error events."""
        result = self.client.search_events(
            query="error",
            limit=limit,
            source="api",
        )
        return result.events

    def close(self):
        """Cleanup."""
        self.client.close()


class AsyncMyAppLogger:
    """Async version for high-throughput logging."""

    def __init__(self, app_name: str):
        self.app_name = app_name

    async def log_batch_events(self, events: list[dict]):
        """Log multiple events concurrently."""
        async with AsyncQuickSearchClient(
            base_url=QUICKSEARCH_URL,
            api_key=API_KEY,
        ) as client:
            event_objects = [
                EventData(
                    type=e["type"],
                    application=self.app_name,
                    message=e.get("message"),
                    data=e.get("data", {}),
                )
                for e in events
            ]

            responses = await client.ingest_events(event_objects)
            logger.info(f"Batch logged {len(responses)} events")
            return [r.eventId for r in responses if r.success]


# ============================================================
# EXAMPLE USAGE
# ============================================================

def example_sync_usage():
    """Example: Synchronous event logging."""
    logger = MyAppLogger("my_app")

    # Log user actions
    logger.log_user_action("user123", "login", ip_address="192.168.1.1")
    logger.log_user_action("user123", "view_page", page="/dashboard")
    logger.log_user_action("user123", "click_button", button="submit")

    # Search for events
    errors = logger.search_recent_errors(limit=5)
    logger.info(f"Found {len(errors)} recent errors")

    logger.close()


async def example_async_usage():
    """Example: Asynchronous batch logging."""
    logger = AsyncMyAppLogger("my_app")

    # Prepare batch of events
    events = [
        {"type": "page_view", "data": {"page": "/home", "duration": 1.2}},
        {"type": "page_view", "data": {"page": "/about", "duration": 0.8}},
        {"type": "page_view", "data": {"page": "/contact", "duration": 2.3}},
        {"type": "click", "data": {"element": "navbar", "link": "pricing"}},
        {"type": "form_submit", "data": {"form": "contact", "success": True}},
    ]

    # Log all at once
    event_ids = await logger.log_batch_events(events)
    logger.info(f"Logged {len(event_ids)} events concurrently")


def example_with_context_manager():
    """Example: Using context manager for automatic cleanup."""
    with QuickSearchClient(base_url=QUICKSEARCH_URL, api_key=API_KEY) as client:
        # Log events
        for i in range(10):
            event = EventData(
                type="batch_test",
                application="demo_app",
                data={"index": i},
            )
            response = client.ingest_event(event)
            print(f"Logged {i+1}/10: {response.eventId}")

        # Search
        result = client.search_events(query="batch_test", limit=10)
        print(f"Found {result.count} events")

    # Client automatically closed


if __name__ == "__main__":
    print("=== Sync Example ===")
    example_sync_usage()

    print("\n=== Async Example ===")
    asyncio.run(example_async_usage())

    print("\n=== Context Manager Example ===")
    example_with_context_manager()
