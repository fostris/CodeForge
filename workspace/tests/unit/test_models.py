import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from src.auth.models import (
    Base,
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    TokenPayload,
    TokenPair,
    RefreshRequest,
)


class TestUserModel:
    def test_user_table_name(self):
        assert User.__tablename__ == "users"

    def test_user_columns(self):
        assert hasattr(User, "id")
        assert hasattr(User, "email")
        assert hasattr(User, "hashed_password")
        assert hasattr(User, "created_at")

    def test_user_repr(self):
        user_id = uuid.uuid4()
        user = User(id=user_id, email="test@example.com", hashed_password="hash")
        repr_str = repr(user)
        assert "User" in repr_str
        assert str(user_id) in repr_str
        assert "test@example.com" in repr_str


class TestUserCreateSchema:
    def test_valid_user_create(self):
        data = {
            "email": "valid@example.com",
            "password": "ValidPass123"
        }
        user = UserCreate(**data)
        assert user.email == "valid@example.com"
        assert user.password == "ValidPass123"

    def test_invalid_email(self):
        with pytest.raises(ValueError):
            UserCreate(email="invalid-email", password="ValidPass123")

    def test_password_too_short(self):
        with pytest.raises(ValueError):
            UserCreate(email="test@example.com", password="short")

    def test_password_too_long(self):
        with pytest.raises(ValueError):
            UserCreate(email="test@example.com", password="a" * 129)

    def test_password_missing_uppercase(self):
        with pytest.raises(ValueError) as exc_info:
            UserCreate(email="test@example.com", password="lowercase123")
        assert "uppercase" in str(exc_info.value).lower()

    def test_password_missing_lowercase(self):
        with pytest.raises(ValueError) as exc_info:
            UserCreate(email="test@example.com", password="UPPERCASE123")
        assert "lowercase" in str(exc_info.value).lower()

    def test_password_missing_digit(self):
        with pytest.raises(ValueError) as exc_info:
            UserCreate(email="test@example.com", password="NoDigitsHere")
        assert "digit" in str(exc_info.value).lower()


class TestUserLoginSchema:
    def test_valid_user_login(self):
        data = {
            "email": "user@example.com",
            "password": "anypassword"
        }
        login = UserLogin(**data)
        assert login.email == "user@example.com"
        assert login.password == "anypassword"

    def test_invalid_email_login(self):
        with pytest.raises(ValueError):
            UserLogin(email="invalid", password="password")


class TestUserResponseSchema:
    def test_from_user_instance(self):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        user = User(
            id=user_id,
            email="response@example.com",
            hashed_password="secret_hash",
            created_at=now
        )
        response = UserResponse.model_validate(user)
        assert response.id == user_id
        assert response.email == "response@example.com"
        assert response.created_at == now
        assert not hasattr(response, "hashed_password")
        assert not hasattr(response, "password")

    def test_direct_construction(self):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        response = UserResponse(
            id=user_id,
            email="direct@example.com",
            created_at=now
        )
        assert response.id == user_id
        assert response.email == "direct@example.com"
        assert response.created_at == now


class TestTokenPayloadSchema:
    def test_token_payload_defaults(self):
        payload = TokenPayload(sub="user123", exp=123456, iat=123000)
        assert payload.sub == "user123"
        assert payload.exp == 123456
        assert payload.iat == 123000
        assert payload.type == "access"

    def test_token_payload_custom_type(self):
        payload = TokenPayload(sub="user123", exp=123456, iat=123000, type="refresh")
        assert payload.type == "refresh"


class TestTokenPairSchema:
    def test_token_pair_defaults(self):
        pair = TokenPair(
            access_token="access_token_123",
            refresh_token="refresh_token_456"
        )
        assert pair.access_token == "access_token_123"
        assert pair.refresh_token == "refresh_token_456"
        assert pair.token_type == "bearer"

    def test_token_pair_custom_type(self):
        pair = TokenPair(
            access_token="access",
            refresh_token="refresh",
            token_type="Bearer"
        )
        assert pair.token_type == "Bearer"


class TestRefreshRequestSchema:
    def test_refresh_request(self):
        req = RefreshRequest(refresh_token="some_refresh_token")
        assert req.refresh_token == "some_refresh_token"