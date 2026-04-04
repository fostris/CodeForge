from typing import Any, Optional


class AuthException(Exception):
    """Base exception for authentication-related errors."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        *args: Any,
        **kwargs: Any
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail, *args, **kwargs)


class AuthenticationError(AuthException):
    """Raised when general authentication fails."""
    
    def __init__(
        self,
        detail: str = "Authentication failed",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(401, detail, *args, **kwargs)


class InvalidCredentialsError(AuthException):
    """Raised when credentials (email/password) are invalid."""
    
    def __init__(
        self,
        detail: str = "Invalid credentials",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(401, detail, *args, **kwargs)


class InvalidTokenError(AuthException):
    """Raised when a token is malformed or invalid."""
    
    def __init__(
        self,
        detail: str = "Invalid token",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(401, detail, *args, **kwargs)


class ExpiredTokenError(AuthException):
    """Raised when a token has expired."""
    
    def __init__(
        self,
        detail: str = "Token has expired",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(401, detail, *args, **kwargs)


class DuplicateEmailError(AuthException):
    """Raised when trying to register with an email that already exists."""
    
    def __init__(
        self,
        detail: str = "Email already registered",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(409, detail, *args, **kwargs)


class RateLimitExceededError(AuthException):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(429, detail, *args, **kwargs)


class ValidationException(AuthException):
    """Raised when input validation fails."""
    
    def __init__(
        self,
        detail: str = "Validation error",
        *args: Any,
        **kwargs: Any
    ) -> None:
        super().__init__(422, detail, *args, **kwargs)