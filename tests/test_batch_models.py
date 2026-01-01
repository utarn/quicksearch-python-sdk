"""
Tests for batch ingestion models.
"""

import pytest

from quicksearch.models import (
    BatchIngestError,
    BatchIngestOptions,
    BatchIngestResult,
)


class TestBatchIngestOptions:
    """Tests for BatchIngestOptions model."""

    def test_default_values(self):
        """Test default values for BatchIngestOptions."""
        options = BatchIngestOptions()

        assert options.batch_size == 100
        assert options.flush_interval == 2.0
        assert options.queue_size_limit == 10000
        assert options.max_concurrency == 5
        assert options.retry_attempts == 3
        assert options.retry_delay == 1.0
        assert options.enabled is False

    def test_custom_values(self):
        """Test creating BatchIngestOptions with custom values."""
        options = BatchIngestOptions(
            batch_size=50,
            flush_interval=5.0,
            queue_size_limit=5000,
            max_concurrency=10,
            retry_attempts=5,
            retry_delay=2.0,
            enabled=True,
        )

        assert options.batch_size == 50
        assert options.flush_interval == 5.0
        assert options.queue_size_limit == 5000
        assert options.max_concurrency == 10
        assert options.retry_attempts == 5
        assert options.retry_delay == 2.0
        assert options.enabled is True

    def test_batch_size_validation(self):
        """Test validation of batch_size field."""
        # Too large
        with pytest.raises(Exception):  # Pydantic ValidationError
            BatchIngestOptions(batch_size=2000)

        # Too small
        with pytest.raises(Exception):
            BatchIngestOptions(batch_size=0)

    def test_flush_interval_validation(self):
        """Test validation of flush_interval field."""
        # Too small
        with pytest.raises(Exception):
            BatchIngestOptions(flush_interval=0.01)

    def test_queue_size_limit_validation(self):
        """Test validation of queue_size_limit field."""
        # Too small
        with pytest.raises(Exception):
            BatchIngestOptions(queue_size_limit=10)

    def test_max_concurrency_validation(self):
        """Test validation of max_concurrency field."""
        # Too large
        with pytest.raises(Exception):
            BatchIngestOptions(max_concurrency=100)

    def test_retry_attempts_validation(self):
        """Test validation of retry_attempts field."""
        # Too large
        with pytest.raises(Exception):
            BatchIngestOptions(retry_attempts=20)

    def test_retry_delay_validation(self):
        """Test validation of retry_delay field."""
        # Too small
        with pytest.raises(Exception):
            BatchIngestOptions(retry_delay=0.01)


class TestBatchIngestError:
    """Tests for BatchIngestError model."""

    def test_create_error_all_fields(self):
        """Test creating BatchIngestError with all fields."""
        error = BatchIngestError(
            event_index=5,
            event_data={"type": "test", "message": "test event"},
            error_message="Validation failed",
            status_code=400,
            retried=True,
        )

        assert error.event_index == 5
        assert error.event_data == {"type": "test", "message": "test event"}
        assert error.error_message == "Validation failed"
        assert error.status_code == 400
        assert error.retried is True

    def test_create_error_minimal(self):
        """Test creating BatchIngestError with minimal fields."""
        error = BatchIngestError(
            event_index=0,
            event_data={},
            error_message="Unknown error",
        )

        assert error.event_index == 0
        assert error.event_data == {}
        assert error.error_message == "Unknown error"
        assert error.status_code is None
        assert error.retried is False


class TestBatchIngestResult:
    """Tests for BatchIngestResult model."""

    def test_create_result_all_fields(self):
        """Test creating BatchIngestResult with all fields."""
        errors = [
            BatchIngestError(
                event_index=5,
                event_data={"type": "test"},
                error_message="Failed",
            )
        ]

        result = BatchIngestResult(
            success_count=80,
            failure_count=20,
            total_count=100,
            errors=errors,
            batch_count=2,
            processing_time_ms=1500,
        )

        assert result.success_count == 80
        assert result.failure_count == 20
        assert result.total_count == 100
        assert len(result.errors) == 1
        assert result.batch_count == 2
        assert result.processing_time_ms == 1500

    def test_create_result_minimal(self):
        """Test creating minimal BatchIngestResult."""
        result = BatchIngestResult(
            success_count=100,
            failure_count=0,
            total_count=100,
        )

        assert result.success_count == 100
        assert result.failure_count == 0
        assert result.total_count == 100
        assert result.errors == []
        assert result.batch_count == 0
        assert result.processing_time_ms is None

    def test_success_rate_property(self):
        """Test success_rate property calculation."""
        result = BatchIngestResult(
            success_count=80,
            failure_count=20,
            total_count=100,
        )

        assert result.success_rate == 80.0

    def test_success_rate_all_success(self):
        """Test success_rate with 100% success."""
        result = BatchIngestResult(
            success_count=100,
            failure_count=0,
            total_count=100,
        )

        assert result.success_rate == 100.0

    def test_success_rate_all_failure(self):
        """Test success_rate with 0% success."""
        result = BatchIngestResult(
            success_count=0,
            failure_count=100,
            total_count=100,
        )

        assert result.success_rate == 0.0

    def test_success_rate_empty(self):
        """Test success_rate with zero events."""
        result = BatchIngestResult(
            success_count=0,
            failure_count=0,
            total_count=0,
        )

        assert result.success_rate == 100.0
