"""
Asynchronous client for QuickSearch API using httpx.
"""

import asyncio
import time
from typing import Any, Union

import httpx

from quicksearch.async_batch_processor import AsyncBatchProcessor, QueueFullError
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
        batch_options: BatchIngestOptions | None = None,
    ) -> None:
        super().__init__(base_url, api_key, jwt_token, timeout, verify_ssl)
        self.limits = limits or httpx.Limits(max_keepalive_connections=5, max_connections=10)
        self._client: httpx.AsyncClient | None = None

        # Batch processing support
        self._batch_options = batch_options or BatchIngestOptions()
        self._batch_processor: AsyncBatchProcessor | None = None

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

        # Start batch processor if enabled
        if self._batch_options.enabled and self._batch_processor is None:
            self._batch_processor = AsyncBatchProcessor(
                ingest_func=self._ingest_batch_internal,
                options=self._batch_options,
            )
            await self._batch_processor.start()

    async def close(self) -> None:
        """Close the async client."""
        # Stop batch processor and flush remaining events
        if self._batch_processor:
            await self._batch_processor.stop()
            self._batch_processor = None

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

    async def ingest_events(
        self,
        events: list[EventData | dict[str, Any]],
        batch_options: BatchIngestOptions | None = None,
    ) -> Union[list[EventResponse], BatchIngestResult]:
        """
        Asynchronously ingest multiple events in batch.

        Args:
            events: List of event data
            batch_options: Optional batch configuration (overrides client default)

        Returns:
            List of EventResponse objects if batching disabled,
            BatchIngestResult if batching enabled
        """
        self._ensure_connected()

        # Convert dicts to EventData
        event_data_list = [
            event if isinstance(event, EventData) else EventData(**event)
            for event in events
        ]

        # Use provided options or client default
        options = batch_options or self._batch_options

        if not options.enabled:
            # Backward compatible: sequential ingestion
            return [await self.ingest_event(event) for event in event_data_list]

        # Use concurrent batch ingestion with partial success
        return await self._ingest_events_with_result(event_data_list, options)

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

    async def ingest_event_batched(
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
            QueueFullError: If buffer is full
        """
        if not self._batch_processor:
            raise RuntimeError("Batching is not enabled. Set batch_options.enabled=True")

        event_data = event if isinstance(event, EventData) else EventData(**event)
        await self._batch_processor.add_event(event_data)

    async def flush_batch(self) -> None:
        """Force an immediate flush of all buffered events."""
        if self._batch_processor:
            await self._batch_processor.force_flush()

    async def _ingest_batch_internal(self, batch: list[EventData]) -> None:
        """Internal method to ingest a batch (called by batch processor)."""
        for event in batch:
            await self.ingest_event(event)

    async def _ingest_events_with_result(
        self,
        events: list[EventData],
        options: BatchIngestOptions,
    ) -> BatchIngestResult:
        """Ingest events concurrently and return detailed result."""
        start_time = time.time()
        errors: list[BatchIngestError] = []
        success_count = 0

        async def ingest_with_retry(event: EventData, index: int) -> tuple[bool, BatchIngestError | None]:
            """Ingest with retry logic."""
            last_error = None

            for attempt in range(options.retry_attempts + 1):
                try:
                    await self.ingest_event(event)
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
                        await asyncio.sleep(delay)

            return False, last_error

        # Process all events concurrently with semaphore
        semaphore = asyncio.Semaphore(options.max_concurrency)

        async def process_one(event: EventData, index: int) -> tuple[bool, BatchIngestError | None]:
            async with semaphore:
                return await ingest_with_retry(event, index)

        results = await asyncio.gather(
            *[process_one(event, i) for i, event in enumerate(events)],
            return_exceptions=True,
        )

        # Collect results
        for result in results:
            if isinstance(result, Exception):
                errors.append(
                    BatchIngestError(
                        event_index=-1,
                        event_data={},
                        error_message=str(result),
                    )
                )
            else:
                success, error = result
                if success:
                    success_count += 1
                elif error:
                    errors.append(error)

        processing_time_ms = int((time.time() - start_time) * 1000)

        return BatchIngestResult(
            success_count=success_count,
            failure_count=len(errors),
            total_count=len(events),
            errors=errors,
            processing_time_ms=processing_time_ms,
        )
