"""
Batch processing utilities for asynchronous client.
"""

import asyncio
from typing import Any, Callable

from quicksearch.models import BatchIngestOptions, EventData


class AsyncBatchProcessor:
    """
    Async batch processor for asynchronous event ingestion.

    Features:
    - Async-safe event buffering
    - Automatic periodic flushing
    - Size-based flushing
    - Graceful shutdown with final flush
    """

    def __init__(
        self,
        ingest_func: Callable[[list[EventData]], Any],
        options: BatchIngestOptions,
    ) -> None:
        """
        Initialize the async batch processor.

        Args:
            ingest_func: Async function to call for ingesting a batch
            options: Batch configuration options
        """
        self._ingest_func = ingest_func
        self._options = options
        self._buffer: list[EventData] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background flush task."""
        if self._flush_task is None or self._flush_task.done():
            self._stop_event.clear()
            self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        """
        Stop the batch processor and flush remaining events.

        This method waits until all queued events are processed.
        """
        self._stop_event.set()

        if self._flush_task and not self._flush_task.done():
            await asyncio.wait_for(self._flush_task, timeout=30.0)

        # Final flush
        await self._flush_remaining()

    async def add_event(self, event: EventData) -> None:
        """
        Add an event to the batch buffer.

        Args:
            event: Event data to buffer

        Raises:
            QueueFullError: If buffer exceeds queue_size_limit
        """
        async with self._lock:
            if len(self._buffer) >= self._options.queue_size_limit:
                raise QueueFullError(
                    f"Batch buffer full ({self._options.queue_size_limit} events)"
                )

            self._buffer.append(event)

    async def force_flush(self) -> None:
        """Force an immediate flush of all buffered events."""
        await self._flush_batch()

    async def _flush_loop(self) -> None:
        """Background task that periodically flushes events."""
        while not self._stop_event.is_set():
            try:
                # Wait for flush interval or stop event
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._options.flush_interval,
                )

                if self._stop_event.is_set():
                    break
            except asyncio.TimeoutError:
                pass  # Normal timeout, continue to flush

            await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Flush a batch of events from the buffer."""
        async with self._lock:
            if not self._buffer:
                return

            # Atomic swap to get current buffer
            batch = self._buffer.copy()
            self._buffer.clear()

        if batch:
            try:
                await self._ingest_func(batch)
            except Exception:  # noqa: BLE001
                # Log error but continue
                pass

    async def _flush_remaining(self) -> None:
        """Flush all remaining events during shutdown."""
        async with self._lock:
            batch = self._buffer.copy()
            self._buffer.clear()

        if batch:
            try:
                await self._ingest_func(batch)
            except Exception:  # noqa: BLE001
                pass


class QueueFullError(Exception):
    """Raised when batch buffer is full."""

    pass
