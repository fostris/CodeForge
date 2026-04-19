"""Auth API routes and exception mappings."""

from __future__ import annotations

from typing import Any, Protocol

try:
    from fastapi import APIRouter, Depends, HTTPException
except Exception:  # pragma: no cover - fallback for environments without FastAPI
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

    class APIRouter:  # type: ignore[override]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.routes = []

        def post(self, *args: Any, **kwargs: Any):
            def decorator(fn):
                self.routes.append(fn)
                return fn

            return decorator

    def Depends(fn):  # type: ignore[misc]
        return fn

from src.auth.exceptions import AuthException, RateLimitExceededError
from src.auth.models import TokenPair, UserLogin


class AuthServiceProtocol(Protocol):
    """Auth service contract used by the route layer."""

    def login(self, credentials: UserLogin) -> TokenPair:
        """Authenticate user and return a token pair."""


class _UnconfiguredAuthService:
    """Default placeholder that forces explicit DI wiring in runtime/tests."""

    def login(self, credentials: UserLogin) -> TokenPair:
        raise RuntimeError("Auth service dependency is not configured")


_auth_service: AuthServiceProtocol = _UnconfiguredAuthService()


router = APIRouter(prefix="/auth", tags=["auth"])


def set_auth_service(service: AuthServiceProtocol) -> None:
    """Set auth service implementation for dependency wiring."""
    global _auth_service
    _auth_service = service


def get_auth_service() -> AuthServiceProtocol:
    """FastAPI dependency provider for auth service."""
    return _auth_service


@router.post("/login", response_model=TokenPair)
def login(credentials: UserLogin, auth_service: AuthServiceProtocol = Depends(get_auth_service)) -> TokenPair:
    """Authenticate user credentials and map domain exceptions to HTTP responses."""
    try:
        return auth_service.login(credentials)
    except RateLimitExceededError as exc:
        # Explicitly map real rate-limit exception to HTTP 429.
        raise HTTPException(status_code=429, detail=exc.detail) from exc
    except AuthException as exc:
        # Preserve non-rate-limit auth exceptions with their own status codes.
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
