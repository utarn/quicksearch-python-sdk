"""
QuickSearch Python SDK

A Python library for interacting with the QuickSearch event log storage system.
"""

from quicksearch._version import __version__
from quicksearch.async_batch_processor import QueueFullError
from quicksearch.async_client import AsyncQuickSearchClient
from quicksearch.client import BaseQuickSearchClient
from quicksearch.exceptions import (
    AuthenticationError,
    ConnectionError,
    PermissionError,
    QuickSearchError,
    RateLimitError,
    ServerError,
    ValidationError,
)
from quicksearch.models import (
    BatchIngestError,
    BatchIngestOptions,
    BatchIngestResult,
    Event,
    EventData,
    EventResponse,
    EventSearchResult,
    SyslogData,
)
from quicksearch.sync_client import QuickSearchClient

__all__ = [
    # Version
    "__version__",
    # Clients
    "BaseQuickSearchClient",
    "QuickSearchClient",
    "AsyncQuickSearchClient",
    # Models
    "EventData",
    "SyslogData",
    "EventResponse",
    "EventSearchResult",
    "Event",
    # Batch models
    "BatchIngestOptions",
    "BatchIngestResult",
    "BatchIngestError",
    # Exceptions
    "QuickSearchError",
    "AuthenticationError",
    "PermissionError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "ConnectionError",
    "QueueFullError",
]

__author__ = "QuickSearch Team"
__email__ = "support@quicksearch.io"
