# QuickSearch Python SDK

[![PyPI version](https://badge.fury.io/py/quicksearch-python-sdk.svg)](https://badge.fury.io/py/quicksearch-python-sdk)
[![Python versions](https://img.shields.io/pypi/pyversions/quicksearch-python-sdk.svg)](https://pypi.org/project/quicksearch-python-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library for interacting with the QuickSearch event log storage system.

## Features

- **Simple API**: Clean, pythonic interface for event ingestion and search
- **Type Safety**: Full type hints and Pydantic models for data validation
- **Async Support**: Both synchronous and asynchronous clients included
- **Error Handling**: Comprehensive exception classes for easy error handling
- **Flexible Authentication**: Support for API keys and JWT tokens

## Installation

```bash
# Using uv
uv add quicksearch-python-sdk

# Using pip
pip install quicksearch-python-sdk
```

## Quick Start

### Synchronous Client

```python
from quicksearch import QuickSearchClient, EventData

# Initialize client
client = QuickSearchClient(
    base_url="http://localhost:3000",
    api_key="your-api-key-here"
)

# Ingest an event
event = EventData(
    type="user_login",
    application="web_app",
    data={"user_id": "12345", "ip_address": "192.168.1.100"}
)

response = client.ingest_event(event)
print(f"Event ID: {response.eventId}")

# Search for events
result = client.search_events(query="login", limit=10)
for event in result.events:
    print(f"{event['timestamp_iso']}: {event['message']}")

# Cleanup
client.close()
```

### Using Context Manager

```python
from quicksearch import QuickSearchClient, EventData

with QuickSearchClient(api_key="your-api-key") as client:
    response = client.ingest_event(EventData(type="test_event"))
    print(f"Success: {response.success}")
```

### Asynchronous Client

```python
import asyncio
from quicksearch import AsyncQuickSearchClient, EventData

async def main():
    async with AsyncQuickSearchClient(api_key="your-api-key") as client:
        # Ingest an event
        event = EventData(type="user_login", data={"user_id": "12345"})
        response = await client.ingest_event(event)
        print(f"Event ID: {response.eventId}")

        # Search for events
        result = await client.search_events(query="login")
        print(f"Found {result.count} events")

asyncio.run(main())
```

## API Reference

### QuickSearchClient (Synchronous)

#### Constructor

```python
QuickSearchClient(
    base_url: str = "http://localhost:3000",
    api_key: str | None = None,
    jwt_token: str | None = None,
    timeout: float = 30.0,
    verify_ssl: bool = True
)
```

#### Methods

##### `ingest_event(event)`

Ingest a single event.

**Parameters:**
- `event` (EventData | dict): Event data

**Returns:** `EventResponse`

**Example:**
```python
event = EventData(
    type="user_login",
    application="web_app",
    message="User logged in",
    data={"user_id": "12345"}
)
response = client.ingest_event(event)
```

##### `ingest_events(events)`

Ingest multiple events in batch.

**Parameters:**
- `events` (list[EventData] | list[dict]): List of event data

**Returns:** `list[EventResponse]`

**Example:**
```python
events = [
    EventData(type="click", data={"button": "submit"}),
    EventData(type="view", data={"page": "home"}),
]
responses = client.ingest_events(events)
```

##### `search_events(**kwargs)`

Search for events.

**Parameters:**
- `query` (str | None): Search query string
- `limit` (int): Maximum results (default: 100)
- `source` (str | None): Filter by source
- `severity` (str | None): Filter by severity
- `timestamp_gte` (str | None): Filter by timestamp (ISO format)

**Returns:** `EventSearchResult`

**Example:**
```python
result = client.search_events(
    query="error",
    source="syslog",
    severity="critical",
    limit=50
)
print(f"Found {result.count} events")
for event in result.events:
    print(event)
```

##### `ingest_syslog(syslog_data)`

Ingest a syslog message.

**Parameters:**
- `syslog_data` (SyslogData | str | dict): Syslog data or raw string

**Returns:** `EventResponse`

**Example:**
```python
# Structured syslog
from quicksearch import SyslogData

syslog = SyslogData(
    severity="error",
    hostname="web-server-01",
    message="Authentication failed",
    data={"user": "admin"}
)
response = client.ingest_syslog(syslog)

# Raw syslog string
raw_syslog = "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for user"
response = client.ingest_syslog(raw_syslog)
```

### AsyncQuickSearchClient (Asynchronous)

The async client has the same methods as the sync client, but all methods are async.

```python
async with AsyncQuickSearchClient(api_key="your-api-key") as client:
    response = await client.ingest_event(EventData(type="test"))
    result = await client.search_events(query="test")
```

## Data Models

### EventData

```python
EventData(
    type: str,                              # Required
    application: str | None = None,
    timestamp: str | None = None,           # ISO 8601 format
    message: str | None = None,
    data: dict[str, Any] = {},
    source: str | None = None
)
```

### SyslogData

```python
SyslogData(
    type: str | None = None,
    severity: str | None = None,
    hostname: str | None = None,
    message: str | None = None,
    data: dict[str, Any] = {}
)
```

### EventResponse

```python
EventResponse(
    success: bool,
    message: str,
    eventId: str | None = None
)
```

### EventSearchResult

```python
EventSearchResult(
    success: bool,
    events: list[dict[str, Any]],
    count: int,
    estimated_total: int | None = None,
    processing_time_ms: int | None = None,
    query: str | None = None
)
```

## Error Handling

The SDK provides specific exception types for different error scenarios:

```python
from quicksearch import (
    QuickSearchClient,
    EventData,
    AuthenticationError,
    PermissionError,
    ValidationError,
    RateLimitError,
    ServerError,
    ConnectionError
)

client = QuickSearchClient(api_key="your-api-key")

try:
    response = client.ingest_event(EventData(type="test"))
except AuthenticationError:
    print("Invalid API key or token")
except PermissionError:
    print("API key lacks required permission")
except ValidationError as e:
    print(f"Invalid data: {e}")
except RateLimitError:
    print("Daily API limit exceeded")
except ServerError:
    print("Server error occurred")
except ConnectionError:
    print("Failed to connect to server")
```

## Authentication

### API Key Authentication

```python
# Via Authorization header (default)
client = QuickSearchClient(api_key="your-api-key")
```

### JWT Token Authentication

```python
client = QuickSearchClient(jwt_token="your-jwt-token")
```

## Testing

The SDK includes comprehensive tests. To run them:

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=quicksearch --cov-report=html
```

## Development

```bash
# Install development dependencies
uv sync --all-extras

# Format code
uv run black quicksearch tests

# Lint code
uv run ruff check quicksearch tests

# Type check
uv run mypy quicksearch
```

## Requirements

- Python 3.9 or higher
- requests >= 2.31.0
- httpx >= 0.25.0
- pydantic >= 2.5.0

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, please visit the [GitHub repository](https://github.com/quicksearch/quicksearch-python-sdk).
