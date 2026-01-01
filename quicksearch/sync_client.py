"""
Synchronous client for QuickSearch API using httpx.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Union

import httpx

from quicksearch.async_batch_processor import QueueFullError
from quicksearch.batch_processor import SyncBatchProcessor
from quicksearch.client import BaseQuickSearchClient
from quicksearch.exceptions import ConnectionError as QuickSearchConnectionError
from quicksearch.models import (
    BatchIngestError,
    BatchIngestOptions,
    BatchIngestResult,
    EventData,
    EventResponse,
    EventSearchResult,
    SyslogData,
)


class QuickSearchClient(BaseQuickSearchClient):
    """Synchronous client for QuickSearch API."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: str | None = None,
        jwt_token: str | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        batch_options: BatchIngestOptions | None = None,
    ) -> None:
        super().__init__(base_url, api_key, jwt_token, timeout, verify_ssl)
        self._client: httpx.Client | None = None
        self._limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._verify_ssl = verify_ssl

        # Batch processing support
        self._batch_options = batch_options or BatchIngestOptions()
        self._batch_processor: SyncBatchProcessor | None = None

        if self._batch_options.enabled:
            self._batch_processor = SyncBatchProcessor(
                ingest_func=self._ingest_batch_internal,
                options=self._batch_options,
            )
            self._batch_processor.start()

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

    def ingest_events(
        self,
        events: list[EventData | dict[str, Any]],
        batch_options: BatchIngestOptions | None = None,
    ) -> Union[list[EventResponse], BatchIngestResult]:
        """
        Ingest multiple events in batch.

        Args:
            events: List of event data
            batch_options: Optional batch configuration (overrides client default)

        Returns:
            List of EventResponse objects if batching disabled,
            BatchIngestResult if batching enabled
        """
        # Convert dicts to EventData
        event_data_list = [
            event if isinstance(event, EventData) else EventData(**event)
            for event in events
        ]

        # Use provided options or client default
        options = batch_options or self._batch_options

        if not options.enabled:
            # Backward compatible: sequential ingestion
            return [self.ingest_event(event) for event in event_data_list]

        # Use concurrent batch ingestion with partial success
        return self._ingest_events_with_result(event_data_list, options)

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
        # Stop batch processor and flush remaining events
        if self._batch_processor:
            self._batch_processor.stop()
            self._batch_processor = None

        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "QuickSearchClient":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()

    def ingest_event_batched(
        self,
        event: EventData | dict[str, Any],
    ) -> None:
        """
        Add a single event to the batch queue (non-blocking).

        The event will be sent in the next batch flush based on
        batch_size or flush_interval triggers.

        Args:
            event: Event data to queue

        Raises:
            RuntimeError: If batching is not enabled
            QueueFullError: If queue is full (timeout exceeded)
        """
        if not self._batch_processor:
            raise RuntimeError("Batching is not enabled. Set batch_options.enabled=True")

        event_data = event if isinstance(event, EventData) else EventData(**event)
        success = self._batch_processor.add_event(event_data)

        if not success:
            raise QueueFullError(
                f"Failed to add event to batch queue (timeout). "
                f"Queue may be full at {self._batch_options.queue_size_limit} events"
            )

    def flush_batch(self) -> None:
        """Force an immediate flush of all queued events."""
        if self._batch_processor:
            self._batch_processor.force_flush()

    def _ingest_batch_internal(self, batch: list[EventData]) -> list[EventResponse]:
        """Internal method to ingest a batch (called by batch processor)."""
        return [self.ingest_event(event) for event in batch]

    def _ingest_events_with_result(
        self,
        events: list[EventData],
        options: BatchIngestOptions,
    ) -> BatchIngestResult:
        """Ingest events concurrently and return detailed result."""
        start_time = time.time()
        errors: list[BatchIngestError] = []
        success_count = 0

        def ingest_with_retry(event: EventData, index: int) -> tuple[bool, BatchIngestError | None]:
            """Ingest with retry logic."""
            last_error = None

            for attempt in range(options.retry_attempts + 1):
                try:
                    self.ingest_event(event)
                    return True, None
                except Exception as e:  # noqa: BLE001
                    status_code = getattr(e, "status_code", None)

                    # Don't retry 4xx errors except 429
                    if status_code and 400 <= status_code < 500 and status_code != 429:
                        last_error = BatchIngestError(
                            event_index=index,
                            event_data=event.model_dump(),
                            error_message=str(e),
                            status_code=status_code,
                            retried=False,
                        )
                        break

                    last_error = BatchIngestError(
                        event_index=index,
                        event_data=event.model_dump(),
                        error_message=str(e),
                        status_code=status_code,
                        retried=attempt > 0,
                    )

                    if attempt < options.retry_attempts:
                        delay = options.retry_delay * (2**attempt)
                        time.sleep(delay)

            return False, last_error

        # Process with thread pool
        with ThreadPoolExecutor(max_workers=options.max_concurrency) as executor:
            futures = {
                executor.submit(ingest_with_retry, event, i): (event, i)
                for i, event in enumerate(events)
            }

            for future in as_completed(futures):
                try:
                    success, error = future.result()
                    if success:
                        success_count += 1
                    elif error:
                        errors.append(error)
                except Exception as e:  # noqa: BLE001
                    errors.append(
                        BatchIngestError(
                            event_index=-1,
                            event_data={},
                            error_message=str(e),
                        )
                    )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return BatchIngestResult(
            success_count=success_count,
            failure_count=len(errors),
            total_count=len(events),
            errors=errors,
            processing_time_ms=processing_time_ms,
        )
