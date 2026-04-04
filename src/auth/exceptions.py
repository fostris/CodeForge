"""Authentication exception hierarchy.

This module defines custom exceptions for authentication-related errors.

Classes:
    AuthenticationError: Base exception for authentication errors.
    InvalidCredentialsError: Raised when credentials are invalid.
    TokenExpiredError: Raised when an authentication token has expired.
    TokenInvalidError: Raised when an authentication token is invalid.
    UserAlreadyExistsError: Raised when attempting to create a user that already exists.
    RateLimitExceededError: Raised when the rate limit for requests is exceeded.
"""

__all__ = [
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "TokenInvalidError",
    "UserAlreadyExistsError",
    "RateLimitExceededError",
]


class AuthenticationError(Exception):
    """Base exception for authentication errors.

    Attributes:
        status_code: HTTP status code associated with the error.
        detail: Human-readable description of the error.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        """Initialize the authentication error.

        Args:
            status_code: HTTP status code associated with the error.
            detail: Human-readable description of the error.
        """
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    def __init__(self, detail: str) -> None:
        """Initialize the invalid credentials error.

        Args:
            detail: Human-readable description of the error.
        """
        super().__init__(status_code=401, detail=detail)


class TokenExpiredError(AuthenticationError):
    """Raised when an authentication token has expired."""

    def __init__(self, detail: str) -> None:
        """Initialize the token expired error.

        Args:
            detail: Human-readable description of the error.
        """
        super().__init__(status_code=401, detail=detail)


class TokenInvalidError(AuthenticationError):
    """Raised when an authentication token is invalid."""

    def __init__(self, detail: str) -> None:
        """Initialize the token invalid error.

        Args:
            detail: Human-readable description of the error.
        """
        super().__init__(status_code=401, detail=detail)


class UserAlreadyExistsError(AuthenticationError):
    """Raised when attempting to create a user that already exists."""

    def __init__(self, detail: str) -> None:
        """Initialize the user already exists error.

        Args:
            detail: Human-readable description of the error.
        """
        super().__init__(status_code=409, detail=detail)


class RateLimitExceededError(AuthenticationError):
    """Raised when the rate limit for requests is exceeded."""

    def __init__(self, detail: str) -> None:
        """Initialize the rate limit exceeded error.

        Args:
            detail: Human-readable description of the error.
        """
        super().__init__(status_code=429, detail=detail)