"""
Base client class with shared logic for both sync and async clients.
"""

from abc import ABC, abstractmethod
from typing import Any

from quicksearch.exceptions import (
    AuthenticationError,
    PermissionError,
    QuickSearchError,
    RateLimitError,
    ServerError,
    ValidationError,
)


class AuthConfig:
    """Configuration for authentication."""

    def __init__(
        self,
        api_key: str | None = None,
        jwt_token: str | None = None,
        auth_method: str = "auto",
    ) -> None:
        self.api_key = api_key
        self.jwt_token = jwt_token
        self.auth_method = auth_method

    def get_headers(self) -> dict[str, str]:
        """Get authentication headers."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        if self.jwt_token:
            return {"Authorization": f"Bearer {self.jwt_token}"}
        return {}

    def get_query_params(self) -> dict[str, str]:
        """Get query parameters for API key authentication."""
        if self.api_key:
            return {"api_key": self.api_key}
        return {}


class BaseQuickSearchClient(ABC):
    """Abstract base class for QuickSearch clients."""

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        api_key: str | None = None,
        jwt_token: str | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.auth = AuthConfig(api_key=api_key, jwt_token=jwt_token)

    def _make_url(self, endpoint: str) -> str:
        """Construct full URL from endpoint."""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def _handle_response(self, status_code: int, response_data: dict[str, Any]) -> dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        if status_code in (200, 201):
            return response_data
        if status_code == 400:
            raise ValidationError(response_data.get("statusMessage", "Validation failed"))
        if status_code == 401:
            raise AuthenticationError(response_data.get("statusMessage", "Authentication required"))
        if status_code == 403:
            raise PermissionError(response_data.get("statusMessage", "Permission denied"))
        if status_code == 429:
            raise RateLimitError(response_data.get("statusMessage", "Rate limit exceeded"))
        if status_code >= 500:
            raise ServerError(response_data.get("statusMessage", "Server error"))
        raise QuickSearchError(f"Unexpected status code: {status_code}", status_code=status_code)

    @abstractmethod
    def ingest_event(self, event: Any) -> Any:
        """Ingest an event."""
        pass

    @abstractmethod
    def search_events(self, **kwargs: Any) -> Any:
        """Search for events."""
        pass

    @abstractmethod
    def ingest_syslog(self, syslog_data: Any) -> Any:
        """Ingest a syslog message."""
        pass
