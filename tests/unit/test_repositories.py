import pytest
from datetime import timedelta
from typing import Optional
from unittest.mock import Mock, patch

from src.auth.repositories import RefreshTokenRepository, RefreshToken

class TestRefreshTokenRepository:

    @pytest.fixture
    def repository(self):
        return RefreshTokenRepository()

    @pytest.fixture
    def mock_hash_function(self, monkeypatch):
        mock = Mock()
        monkeypatch.setattr('src.auth.repositories.hashlib.sha256', mock)
        return mock

    @pytest.fixture
    def mock_token_model(self):
        with patch('src.auth.repositories.RefreshToken') as mock:
            yield mock

    def test_create_hashes_token_and_stores_with_expiration(
        self, repository, mock_hash_function, mock_token_model
    ):
        token_value = 'test_token'
        expires_in = timedelta(days=1)
        
        repository.create(token_value, expires_in)
        
        mock_hash_function.assert_called_once_with(token_value.encode())
        mock_token_model.objects.create.assert_called_once_with(
            token_hash=mock_hash_function.return_value.hexdigest(),
            expires_at=(repository.now() + expires_in),
            revoked=False
        )

    def test_get_valid_token_checks_hash_and_expiration(
        self, repository, mock_hash_function, mock_token_model
    ):
        token_value = 'test_token'
        expires_in = timedelta(days=1)
        
        repository.create(token_value, expires_in)
        
        with patch('src.auth.repositories.datetime') as mock_datetime:
            mock_datetime.now.return_value = repository.now() + (expires_in / 2)
            result = repository.get_valid_token(mock_hash_function.return_value.hexdigest())
            
            assert result == mock_token_model.objects.create.return_value

    def test_get_valid_token_returns_none_if_invalid(
        self, repository, mock_hash_function, mock_token_model
    ):
        token_value = 'test_token'
        expires_in = timedelta(days=1)
        
        repository.create(token_value, expires_in)
        
        with patch('src.auth.repositories.datetime') as mock_datetime:
            mock_datetime.now.return_value = repository.now() + (expires_in * 2)
            result = repository.get_valid_token(mock_hash_function.return_value.hexdigest())
            
            assert result is None

    def test_revoke_sets_revoked_to_true_for_token_hash(
        self, repository, mock_token_model
    ):
        token_hash = 'test_hash'

        repository.revoke(token_hash)

        mock_token_model.objects.filter.assert_called_once_with(token_hash=token_hash)
        mock_token_model.objects.filter.return_value.update.assert_called_once_with(revoked=True)

    def test_revoke_all_for_user_returns_count_of_revoked_tokens(
        self, repository, mock_token_model
    ):
        user_id = 'test_user'
        
        result = repository.revoke_all_for_user(user_id)
        
        assert result == mock_token_model.objects.filter.return_value.update.return_value