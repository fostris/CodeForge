import pytest

from src.auth.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    UserAlreadyExistsError,
    RateLimitExceededError,
)

def test_authentication_error():
    error = AuthenticationError(status_code=401, detail="Unauthorized")
    assert error.status_code == 401
    assert error.detail == "Unauthorized"

def test_invalid_credentials_error():
    error = InvalidCredentialsError(detail="Invalid credentials")
    assert isinstance(error, AuthenticationError)
    assert error.status_code == 401
    assert error.detail == "Invalid credentials"

def test_token_expired_error():
    error = TokenExpiredError(detail="Token has expired")
    assert isinstance(error, AuthenticationError)
    assert error.status_code == 401
    assert error.detail == "Token has expired"

def test_token_invalid_error():
    error = TokenInvalidError(detail="Token is invalid")
    assert isinstance(error, AuthenticationError)
    assert error.status_code == 401
    assert error.detail == "Token is invalid"

def test_user_already_exists_error():
    error = UserAlreadyExistsError(detail="User already exists")
    assert isinstance(error, AuthenticationError)
    assert error.status_code == 409
    assert error.detail == "User already exists"

def test_rate_limit_exceeded_error():
    error = RateLimitExceededError(detail="Rate limit exceeded")
    assert isinstance(error, AuthenticationError)
    assert error.status_code == 429
    assert error.detail == "Rate limit exceeded"