import pytest
from pydantic import ValidationError
from src.auth.schemas import UserCreate, UserLogin, UserResponse, TokenResponse, RefreshRequest

def test_user_create_validates_email():
    data = {
        "email": "test@example.com",
        "password": "P@ssw0rd!"
    }
    schema = UserCreate(**data)
    assert isinstance(schema, UserCreate)

def test_user_create_invalidates_weak_password():
    data = {
        "email": "test@example.com",
        "password": "pass"
    }
    with pytest.raises(ValidationError):
        UserCreate(**data)

def test_user_login_validates_email_and_password():
    data = {
        "email": "test@example.com",
        "password": "P@ssw0rd!"
    }
    schema = UserLogin(**data)
    assert isinstance(schema, UserLogin)

def test_token_response_includes_access_and_refresh_tokens():
    data = {
        "access_token": "abc123",
        "refresh_token": "def456"
    }
    schema = TokenResponse(**data)
    assert isinstance(schema, TokenResponse)
    assert hasattr(schema, "access_token")
    assert hasattr(schema, "refresh_token")

def test_user_response_serializable():
    data = {
        "id": 1,
        "email": "test@example.com",
        "username": "user"
    }
    schema = UserResponse(**data)
    serialized = schema.json()
    assert isinstance(serialized, str)

def test_refresh_request_validates_token():
    data = {
        "refresh_token": "abc123"
    }
    schema = RefreshRequest(**data)
    assert isinstance(schema, RefreshRequest)