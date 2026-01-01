"""
Batch processing utilities for synchronous client.
"""

import threading
import time
from collections import deque
from queue import Empty, Queue
from typing import Any, Callable

from quicksearch.models import BatchIngestOptions, EventData


class SyncBatchProcessor:
    """
    Thread-safe batch processor for synchronous event ingestion.

    Features:
    - Thread-safe event queueing
    - Automatic periodic flushing
    - Size-based flushing
    - Graceful shutdown with final flush
    - Queue limit with backpressure
    """

    def __init__(
        self,
        ingest_func: Callable[[list[EventData]], list[Any]],
        options: BatchIngestOptions,
    ) -> None:
        """
        Initialize the batch processor.

        Args:
            ingest_func: Function to call for ingesting a batch of events
            options: Batch configuration options
        """
        self._ingest_func = ingest_func
        self._options = options
        self._queue: Queue[EventData] = Queue(maxsize=options.queue_size_limit)
        self._lock = threading.RLock()
        self._flush_event = threading.Event()
        self._stop_event = threading.Event()
        self._flush_thread: threading.Thread | None = None
        self._pending_count = 0

    def start(self) -> None:
        """Start the background flush thread."""
        with self._lock:
            if self._flush_thread is None or not self._flush_thread.is_alive():
                self._stop_event.clear()
                self._flush_thread = threading.Thread(
                    target=self._flush_loop,
                    name="QuickSearchBatchFlush",
                    daemon=True,
                )
                self._flush_thread.start()

    def stop(self) -> None:
        """
        Stop the batch processor and flush remaining events.

        This method blocks until all queued events are processed.
        """
        with self._lock:
            self._stop_event.set()
            self._flush_event.set()  # Wake up the flush thread

        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=30.0)

        # Final flush of any remaining events
        self._flush_remaining()

    def add_event(self, event: EventData, timeout: float = 5.0) -> bool:
        """
        Add an event to the batch queue.

        Args:
            event: Event data to queue
            timeout: Maximum time to wait if queue is full

        Returns:
            True if event was queued, False if timeout exceeded
        """
        try:
            self._queue.put(event, block=True, timeout=timeout)
            with self._lock:
                self._pending_count += 1

            # Trigger flush if batch size reached
            with self._lock:
                if self._pending_count >= self._options.batch_size:
                    self._flush_event.set()

            return True
        except Exception:  # noqa: BLE001
            return False

    def force_flush(self) -> None:
        """Force an immediate flush of all queued events."""
        self._flush_event.set()

    def _flush_loop(self) -> None:
        """Background thread that periodically flushes events."""
        while not self._stop_event.is_set():
            # Wait for flush interval or flush event
            self._flush_event.wait(timeout=self._options.flush_interval)
            self._flush_event.clear()

            if self._stop_event.is_set():
                break

            self._flush_batch()

    def _flush_batch(self) -> None:
        """Flush a batch of events from the queue."""
        if self._queue.empty():
            return

        batch: list[EventData] = []
        with self._lock:
            # Collect up to batch_size events
            while len(batch) < self._options.batch_size and not self._queue.empty():
                try:
                    event = self._queue.get_nowait()
                    batch.append(event)
                except Empty:
                    break

            self._pending_count -= len(batch)

        if batch:
            try:
                self._ingest_func(batch)
            except Exception:  # noqa: BLE001
                # Log error but continue processing
                pass

    def _flush_remaining(self) -> None:
        """Flush all remaining events during shutdown."""
        batch: list[EventData] = []

        with self._lock:
            while not self._queue.empty():
                try:
                    event = self._queue.get_nowait()
                    batch.append(event)
                except Empty:
                    break

            self._pending_count = 0

        if batch:
            try:
                self._ingest_func(batch)
            except Exception:  # noqa: BLE001
                pass
