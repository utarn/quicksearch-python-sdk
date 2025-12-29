"""
Asynchronous client for QuickSearch API using httpx.
"""

from typing import Any

import httpx

from quicksearch.client import BaseQuickSearchClient
from quicksearch.exceptions import ConnectionError as QuickSearchConnectionError
from quicksearch.models import EventData, EventResponse, EventSearchResult, SyslogData


class AsyncQuickSearchClient(BaseQuickSearchClient):
    """Asynchronous client for QuickSearch API."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: str | None = None,
        jwt_token: str | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        limits: httpx.Limits | None = None,
    ) -> None:
        super().__init__(base_url, api_key, jwt_token, timeout, verify_ssl)
        self.limits = limits or httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncQuickSearchClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()

    async def connect(self) -> None:
        """Initialize the async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=self.verify_ssl,
                limits=self.limits,
            )

    async def close(self) -> None:
        """Close the async client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _ensure_connected(self) -> None:
        """Ensure client is connected."""
        if self._client is None:
            raise RuntimeError("Client not connected. Use 'async with' or call 'connect()' first.")

    async def ingest_event(self, event: EventData | dict[str, Any]) -> EventResponse:
        """
        Asynchronously ingest an event into QuickSearch.

        Args:
            event: Event data as EventData model or dictionary

        Returns:
            EventResponse: Response containing success status and event ID
        """
        self._ensure_connected()
        assert self._client is not None

        if isinstance(event, dict):
            event = EventData(**event)

        headers = {"Content-Type": "application/json", **self.auth.get_headers()}
        params = self.auth.get_query_params()

        try:
            response = await self._client.post(
                "/api/events",
                json=event.model_dump(exclude_none=True),
                headers=headers,
                params=params,
            )
        except httpx.RequestError as e:
            raise QuickSearchConnectionError(f"Connection error: {e}") from e

        data = self._handle_response(response.status_code, response.json())
        return EventResponse(**data)

    async def ingest_events(self, events: list[EventData | dict[str, Any]]) -> list[EventResponse]:
        """
        Asynchronously ingest multiple events in batch.

        Args:
            events: List of event data

        Returns:
            List of EventResponse objects
        """
        return [await self.ingest_event(event) for event in events]

    async def search_events(
        self,
        query: str | None = None,
        limit: int = 100,
        source: str | None = None,
        severity: str | None = None,
        timestamp_gte: str | None = None,
        **kwargs: Any,
    ) -> EventSearchResult:
        """
        Asynchronously search for events in QuickSearch.

        Args:
            query: Search query string
            limit: Maximum number of results (1-1000)
            source: Filter by source
            severity: Filter by severity
            timestamp_gte: Filter by timestamp (ISO format)
            **kwargs: Additional search parameters

        Returns:
            EventSearchResult: Search results with event list and metadata
        """
        self._ensure_connected()
        assert self._client is not None

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
            response = await self._client.get(
                "/api/events",
                params={**params, **auth_params},
                headers=headers,
            )
        except httpx.RequestError as e:
            raise QuickSearchConnectionError(f"Connection error: {e}") from e

        data = self._handle_response(response.status_code, response.json())
        return EventSearchResult(**data)

    async def ingest_syslog(self, syslog_data: SyslogData | str | dict[str, Any]) -> EventResponse:
        """
        Asynchronously ingest a syslog message into QuickSearch.

        Args:
            syslog_data: Syslog data as SyslogData model, raw string, or dictionary

        Returns:
            EventResponse: Response containing success status and event ID
        """
        self._ensure_connected()
        assert self._client is not None

        headers = {"Content-Type": "application/json", **self.auth.get_headers()}
        params = self.auth.get_query_params()

        try:
            if isinstance(syslog_data, str):
                response = await self._client.post(
                    "/api/syslog",
                    content=syslog_data,
                    headers=headers,
                    params=params,
                )
            elif isinstance(syslog_data, dict):
                syslog = SyslogData(**syslog_data)
                response = await self._client.post(
                    "/api/syslog",
                    json=syslog.model_dump(exclude_none=True),
                    headers=headers,
                    params=params,
                )
            else:
                response = await self._client.post(
                    "/api/syslog",
                    json=syslog_data.model_dump(exclude_none=True),
                    headers=headers,
                    params=params,
                )
        except httpx.RequestError as e:
            raise QuickSearchConnectionError(f"Connection error: {e}") from e

        data = self._handle_response(response.status_code, response.json())
        return EventResponse(**data)
