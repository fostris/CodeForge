import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import HTTPException

from src.api_routes import login
from src.auth.exceptions import InvalidCredentialsError, RateLimitExceededError
from src.auth.models import TokenPair, UserLogin


class _RateLimitedAuthService:
    def login(self, credentials: UserLogin) -> TokenPair:
        raise RateLimitExceededError("Too many login attempts")


class _InvalidCredsAuthService:
    def login(self, credentials: UserLogin) -> TokenPair:
        raise InvalidCredentialsError("Invalid credentials")


class _SuccessAuthService:
    def login(self, credentials: UserLogin) -> TokenPair:
        return TokenPair(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
        )


def test_rate_limit_maps_to_429() -> None:
    credentials = UserLogin(email="user@example.com", password="Password123")

    with pytest.raises(HTTPException) as exc_info:
        login(credentials, auth_service=_RateLimitedAuthService())

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "Too many login attempts"


def test_auth_error_does_not_map_to_429() -> None:
    credentials = UserLogin(email="user@example.com", password="Password123")

    with pytest.raises(HTTPException) as exc_info:
        login(credentials, auth_service=_InvalidCredsAuthService())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


def test_login_success_path_returns_tokens() -> None:
    credentials = UserLogin(email="user@example.com", password="Password123")

    result = login(credentials, auth_service=_SuccessAuthService())

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"
    assert result.token_type == "bearer"
