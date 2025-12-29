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
