"""
Pydantic models for data validation and serialization.

These models provide type safety and automatic validation for all
API requests and responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventData(BaseModel):
    """Represents an event to be ingested via the REST API."""

    type: str = Field(..., description="Event type (required)")
    application: str | None = Field(None, description="Application name")
    timestamp: str | None = Field(None, description="ISO format timestamp")
    message: str | None = Field(None, description="Event message")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional event data")
    source: str | None = Field(None, description="Event source (api or syslog)")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            # Validate ISO 8601 format
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError as e:
            raise ValueError("timestamp must be in ISO 8601 format") from e
        return v


class SyslogData(BaseModel):
    """Represents a syslog event to be ingested."""

    type: str | None = Field(None, description="Event type")
    severity: str | None = Field(None, description="Severity level")
    hostname: str | None = Field(None, description="Hostname")
    message: str | None = Field(None, description="Syslog message")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional syslog data")


class EventResponse(BaseModel):
    """Response from event ingestion."""

    success: bool
    message: str
    eventId: str | None = None


class EventSearchResult(BaseModel):
    """Response from event search."""

    success: bool
    events: list[dict[str, Any]]
    count: int
    estimated_total: int | None = None
    processing_time_ms: int | None = None
    query: str | None = None


class Event(BaseModel):
    """Represents a retrieved event."""

    id: str | None = None
    timestamp: int | str
    timestamp_iso: str | None = None
    type: str
    source: str
    application: str | None = None
    message: str | None = None
    data: dict[str, Any] | None = None


class BatchIngestOptions(BaseModel):
    """Configuration for batch ingestion behavior."""

    batch_size: int = Field(default=100, ge=1, le=1000, description="Max events per batch")
    flush_interval: float = Field(default=2.0, ge=0.1, le=60.0, description="Seconds between automatic flushes")
    queue_size_limit: int = Field(default=10000, ge=100, description="Max queued events before blocking")
    max_concurrency: int = Field(default=5, ge=1, le=20, description="Max parallel HTTP requests")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts for failed events")
    retry_delay: float = Field(default=1.0, ge=0.1, le=30.0, description="Initial retry delay in seconds (exponential backoff)")
    enabled: bool = Field(default=False, description="Enable automatic batching")


class BatchIngestError(BaseModel):
    """Details about a failed batch ingestion."""

    event_index: int = Field(description="Index of the event in the original batch")
    event_data: dict[str, Any] = Field(description="The event data that failed")
    error_message: str = Field(description="Error message")
    status_code: int | None = Field(default=None, description="HTTP status code if applicable")
    retried: bool = Field(default=False, description="Whether this error was retried")


class BatchIngestResult(BaseModel):
    """Result from batch ingestion with partial success support."""

    success_count: int = Field(description="Number of successfully ingested events")
    failure_count: int = Field(description="Number of failed events")
    total_count: int = Field(description="Total number of events processed")
    errors: list[BatchIngestError] = Field(default_factory=list, description="Detailed error information")
    batch_count: int = Field(default=0, description="Number of batches sent")
    processing_time_ms: int | None = Field(default=None, description="Total processing time in milliseconds")

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_count == 0:
            return 100.0
        return (self.success_count / self.total_count) * 100
