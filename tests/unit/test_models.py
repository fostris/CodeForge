import pytest
from datetime import datetime, timedelta
from src.auth.models import RefreshToken
from unittest.mock import patch

@pytest.fixture
def mock_user():
    return {"id": 1}

@patch("src.auth.models.get_current_timestamp", return_value=datetime.utcnow())
@patch("src.auth.models.User")
def test_refresh_token_creation(mock_user, mock_get_timestamp):
    # Arrange
    token_hash = "hashed_token"
    user_id = 1
    
    # Act
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        user=mock_user,
        expires_at=None,
        revoked=False
    )
    
    # Assert
    assert isinstance(refresh_token, RefreshToken)
    assert refresh_token.id is None
    assert refresh_token.token_hash == token_hash
    assert refresh_token.user_id == user_id
    assert isinstance(refresh_token.created_at, datetime)
    assert refresh_token.expires_at is None
    assert not refresh_token.revoked

@patch("src.auth.models.get_current_timestamp", return_value=datetime.utcnow())
@patch("src.auth.models.User")
def test_refresh_token_creation_with_expires(mock_user, mock_get_timestamp):
    # Arrange
    token_hash = "hashed_token"
    user_id = 1
    expires_at = datetime.utcnow() + timedelta(days=1)
    
    # Act
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        user=mock_user,
        expires_at=expires_at,
        revoked=False
    )
    
    # Assert
    assert isinstance(refresh_token, RefreshToken)
    assert refresh_token.id is None
    assert refresh_token.token_hash == token_hash
    assert refresh_token.user_id == user_id
    assert isinstance(refresh_token.created_at, datetime)
    assert refresh_token.expires_at == expires_at
    assert not refresh_token.revoked

@patch("src.auth.models.get_current_timestamp", return_value=datetime.utcnow())
@patch("src.auth.models.User")
def test_refresh_token_revoke(mock_user, mock_get_timestamp):
    # Arrange
    token_hash = "hashed_token"
    user_id = 1
    
    # Act
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        user=mock_user,
        expires_at=None,
        revoked=False
    )
    refresh_token.revoke()
    
    # Assert
    assert refresh_token.revoked

@patch("src.auth.models.get_current_timestamp", return_value=datetime.utcnow())
@patch("src.auth.models.User")
def test_refresh_token_revoked_already(mock_user, mock_get_timestamp):
    # Arrange
    token_hash = "hashed_token"
    user_id = 1
    
    # Act
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        user=mock_user,
        expires_at=None,
        revoked=True
    )
    with pytest.raises(Exception) as exc_info:
        refresh_token.revoke()
    
    # Assert
    assert "already revoked" in str(exc_info.value)