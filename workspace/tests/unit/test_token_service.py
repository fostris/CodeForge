import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from src.auth.exceptions import ExpiredTokenError, InvalidTokenError
from src.auth.models import TokenPair
from src.auth.services.token_service import TokenService
from src.config import Settings


class TestTokenService:
    """Test suite for TokenService."""

    @pytest.fixture
    def token_service(self) -> TokenService:
        """Create a TokenService instance for testing."""
        return TokenService()

    @pytest.fixture
    def mock_settings(self) -> Settings:
        """Create mock settings for testing."""
        return Settings(
            jwt_secret="test-secret-key",
            jwt_access_token_expire_minutes=1440,  # 24 hours
            jwt_refresh_token_expire_days=7,
        )

    def test_token_service_initialization(self, mock_settings: Settings) -> None:
        """Test TokenService initialization with settings."""
        with patch("src.auth.services.token_service.get_settings", return_value=mock_settings):
            service = TokenService()
            assert service.secret_key == "test-secret-key"
            assert service.algorithm == "HS256"
            assert service.access_token_expire_minutes == 1440
            assert service.refresh_token_expire_days == 7

    def test_create_access_token(self, token_service: TokenService) -> None:
        """Test creating an access token with correct claims."""
        user_id = "user-123"
        email = "test@example.com"
        
        token = token_service.create_access_token(user_id, email)
        
        # Decode without validation to check payload
        payload = token_service.decode_token(token)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        
        # Verify token can be validated
        validated_payload = token_service.validate_token(token, "access")
        assert validated_payload["sub"] == user_id

    def test_create_refresh_token(self, token_service: TokenService) -> None:
        """Test creating a refresh token with correct claims."""
        user_id = "user-123"
        
        token = token_service.create_refresh_token(user_id)
        
        # Decode without validation to check payload
        payload = token_service.decode_token(token)
        
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        assert "email" not in payload  # Refresh token should not contain email
        
        # Verify token can be validated
        validated_payload = token_service.validate_token(token, "refresh")
        assert validated_payload["sub"] == user_id

    def test_create_token_pair(self, token_service: TokenService) -> None:
        """Test creating a token pair."""
        user_id = "user-123"
        email = "test@example.com"
        
        token_pair = token_service.create_token_pair(user_id, email)
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.token_type == "bearer"
        
        # Verify both tokens are valid
        access_payload = token_service.validate_token(token_pair.access_token, "access")
        refresh_payload = token_service.validate_token(token_pair.refresh_token, "refresh")
        
        assert access_payload["sub"] == user_id
        assert access_payload["email"] == email
        assert refresh_payload["sub"] == user_id
        assert "email" not in refresh_payload

    def test_validate_token_valid(self, token_service: TokenService) -> None:
        """Test validating a valid token."""
        user_id = "user-123"
        email = "test@example.com"
        
        token = token_service.create_access_token(user_id, email)
        payload = token_service.validate_token(token)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"

    def test_validate_token_invalid_signature(self, token_service: TokenService) -> None:
        """Test validating a token with invalid signature."""
        # Create a token with wrong secret
        wrong_secret_token = jwt.encode(
            {"sub": "user-123", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
            "wrong-secret",
            algorithm="HS256"
        )
        
        with pytest.raises(InvalidTokenError):
            token_service.validate_token(wrong_secret_token)

    def test_validate_token_expired(self, token_service: TokenService) -> None:
        """Test validating an expired token."""
        # Create an expired token
        expired_payload = {
            "sub": "user-123",
            "exp": datetime.now(timezone.utc) - timedelta(days=1),
            "iat": datetime.now(timezone.utc) - timedelta(days=2),
            "type": "access"
        }
        expired_token = jwt.encode(
            expired_payload,
            token_service.secret_key,
            algorithm=token_service.algorithm
        )
        
        with pytest.raises(ExpiredTokenError):
            token_service.validate_token(expired_token)

    def test_validate_token_wrong_type(self, token_service: TokenService) -> None:
        """Test validating a token with wrong type."""
        refresh_token = token_service.create_refresh_token("user-123")
        
        with pytest.raises(InvalidTokenError):
            token_service.validate_token(refresh_token, "access")

    def test_validate_token_malformed(self, token_service: TokenService) -> None:
        """Test validating a malformed token."""
        with pytest.raises(InvalidTokenError):
            token_service.validate_token("not-a-valid-token")

    def test_decode_token(self, token_service: TokenService) -> None:
        """Test decoding a token without validation."""
        # Create a token
        user_id = "user-123"
        email = "test@example.com"
        token = token_service.create_access_token(user_id, email)
        
        # Decode it
        payload = token_service.decode_token(token)
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"
        
        # Test with expired token - should still decode
        expired_payload = {
            "sub": "user-456",
            "exp": datetime.now(timezone.utc) - timedelta(days=1),
            "iat": datetime.now(timezone.utc) - timedelta(days=2),
            "type": "access"
        }
        expired_token = jwt.encode(
            expired_payload,
            token_service.secret_key,
            algorithm=token_service.algorithm
        )
        
        expired_decoded = token_service.decode_token(expired_token)
        assert expired_decoded["sub"] == "user-456"
        
        # Test with invalid token
        with pytest.raises(InvalidTokenError):
            token_service.decode_token("not-a-valid-token")