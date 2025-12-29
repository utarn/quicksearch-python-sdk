"""
Synchronous client for QuickSearch API using httpx.
"""

from typing import Any

import httpx

from quicksearch.client import BaseQuickSearchClient
from quicksearch.exceptions import ConnectionError as QuickSearchConnectionError
from quicksearch.models import EventData, EventResponse, EventSearchResult, SyslogData


class QuickSearchClient(BaseQuickSearchClient):
    """Synchronous client for QuickSearch API."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: str | None = None,
        jwt_token: str | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        super().__init__(base_url, api_key, jwt_token, timeout, verify_ssl)
        self._client: httpx.Client | None = None
        self._limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._verify_ssl = verify_ssl

    @property
    def client(self) -> httpx.Client:
        """Lazy initialization of httpx client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=self._verify_ssl,
                limits=self._limits,
            )
        return self._client

    def ingest_event(self, event: EventData | dict[str, Any]) -> EventResponse:
        """
        Ingest an event into QuickSearch.

        Args:
            event: Event data as EventData model or dictionary

        Returns:
            EventResponse: Response containing success status and event ID

        Raises:
            ValidationError: If event data is invalid
            AuthenticationError: If authentication fails
            PermissionError: If API key lacks events:write permission
            QuickSearchError: For other errors

        Example:
            >>> client = QuickSearchClient(api_key="your-api-key")
            >>> event = EventData(type="user_login", application="web_app", data={"user_id": "123"})
            >>> response = client.ingest_event(event)
            >>> print(f"Event ID: {response.eventId}")
        """
        if isinstance(event, dict):
            event = EventData(**event)

        headers = {"Content-Type": "application/json", **self.auth.get_headers()}
        params = self.auth.get_query_params()

        try:
            response = self.client.post(
                "/api/events",
                json=event.model_dump(exclude_none=True),
                headers=headers,
                params=params,
            )
        except httpx.RequestError as e:
            raise QuickSearchConnectionError(f"Connection error: {e}") from e

        data = self._handle_response(response.status_code, response.json())
        return EventResponse(**data)

    def ingest_events(self, events: list[EventData | dict[str, Any]]) -> list[EventResponse]:
        """
        Ingest multiple events in batch.

        Args:
            events: List of event data

        Returns:
            List of EventResponse objects
        """
        return [self.ingest_event(event) for event in events]

    def search_events(
        self,
        query: str | None = None,
        limit: int = 100,
        source: str | None = None,
        severity: str | None = None,
        timestamp_gte: str | None = None,
        **kwargs: Any,
    ) -> EventSearchResult:
        """
        Search for events in QuickSearch.

        Args:
            query: Search query string
            limit: Maximum number of results (1-1000)
            source: Filter by source
            severity: Filter by severity
            timestamp_gte: Filter by timestamp (ISO format, greater than or equal)
            **kwargs: Additional search parameters

        Returns:
            EventSearchResult: Search results with event list and metadata

        Raises:
            AuthenticationError: If authentication fails
            PermissionError: If API key lacks events:read permission
            QuickSearchError: For other errors

        Example:
            >>> result = client.search_events(query="error", limit=50)
            >>> print(f"Found {result.count} events")
            >>> for event in result.events:
            ...     print(f"{event['timestamp']}: {event['message']}")
        """
        params = {
            "q": query,
            "limit": limit,
            "source": source,
            "severity": severity,
            "timestamp_gte": timestamp_gte,
            **kwargs,
        }
        params = {k: v for k, v in params.items() if v is not None}

        headers = self.auth.get_headers()
        auth_params = self.auth.get_query_params()

        try:
            response = self.client.get(
                "/api/events",
                params={**params, **auth_params},
                headers=headers,
            )
        except httpx.RequestError as e:
            raise QuickSearchConnectionError(f"Connection error: {e}") from e

        data = self._handle_response(response.status_code, response.json())
        return EventSearchResult(**data)

    def ingest_syslog(self, syslog_data: SyslogData | str | dict[str, Any]) -> EventResponse:
        """
        Ingest a syslog message into QuickSearch.

        Args:
            syslog_data: Syslog data as SyslogData model, raw string, or dictionary

        Returns:
            EventResponse: Response containing success status and event ID

        Raises:
            ValidationError: If syslog data is invalid
            AuthenticationError: If authentication fails
            PermissionError: If API key lacks syslog:write permission
            QuickSearchError: For other errors

        Example:
            >>> syslog = SyslogData(
            ...     severity="error",
            ...     hostname="web-server-01",
            ...     message="Authentication failed"
            ... )
            >>> response = client.ingest_syslog(syslog)
            >>>
            >>> # Or use raw syslog string:
            >>> raw_syslog = "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for user"
            >>> response = client.ingest_syslog(raw_syslog)
        """
        headers = {"Content-Type": "application/json", **self.auth.get_headers()}
        params = self.auth.get_query_params()

        try:
            if isinstance(syslog_data, str):
                # Raw syslog string
                response = self.client.post(
                    "/api/syslog",
                    content=syslog_data,
                    headers=headers,
                    params=params,
                )
            elif isinstance(syslog_data, dict):
                # Dictionary - convert to SyslogData
                syslog = SyslogData(**syslog_data)
                response = self.client.post(
                    "/api/syslog",
                    json=syslog.model_dump(exclude_none=True),
                    headers=headers,
                    params=params,
                )
            else:
                # SyslogData model
                response = self.client.post(
                    "/api/syslog",
                    json=syslog_data.model_dump(exclude_none=True),
                    headers=headers,
                    params=params,
                )
        except httpx.RequestError as e:
            raise QuickSearchConnectionError(f"Connection error: {e}") from e

        data = self._handle_response(response.status_code, response.json())
        return EventResponse(**data)

    def close(self) -> None:
        """Close the session and release resources."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "QuickSearchClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()
