"""
Custom exceptions for the QuickSearch Python SDK.

All exceptions inherit from QuickSearchError for easy exception handling.
"""


class QuickSearchError(Exception):
    """Base exception for all QuickSearch errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(QuickSearchError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, status_code=401)


class PermissionError(QuickSearchError):
    """Raised when API key lacks required permissions (403)."""

    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, status_code=403)


class RateLimitError(QuickSearchError):
    """Raised when daily API key limit is exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded") -> None:
        super().__init__(message, status_code=429)


class ValidationError(QuickSearchError):
    """Raised when request validation fails (400)."""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, status_code=400)


class ServerError(QuickSearchError):
    """Raised when server error occurs (500)."""

    def __init__(self, message: str = "Server error") -> None:
        super().__init__(message, status_code=500)


class ConnectionError(QuickSearchError):
    """Raised when connection to server fails."""

    def __init__(self, message: str = "Connection failed") -> None:
        super().__init__(message, status_code=None)
