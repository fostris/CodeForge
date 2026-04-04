import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.auth.models import Base, User
from src.config import Settings, get_settings, get_logger
import os

@pytest.fixture
def db_session():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def mock_settings():
    with patch.dict('os.environ', {
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL': 'sqlite://',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'JWT_ALGORITHM': 'HS256',
        'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
        'REFRESH_TOKEN_EXPIRE_DAYS': '7',
        'LOG_LEVEL': 'INFO'
    }):
        settings = Settings()
        return settings

@pytest.fixture
def test_user_data():
    return {
        'email': 'test@example.com',
        'password': 'testpassword123',
        'hashed_password': '$2b$12$fakehashedpasswordstring1234567890'
    }

@pytest.fixture
def sample_tokens():
    return {
        'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
        'refresh_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.different_signature_here'
    }

def test_db_session_fixture(db_session):
    assert db_session is not None
    user = User(email='fixture@test.com', hashed_password='hashed123')
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    assert user.email == 'fixture@test.com'

def test_mock_settings_fixture(mock_settings):
    assert isinstance(mock_settings, Settings)
    assert mock_settings.secret_key == 'test-secret-key'
    assert mock_settings.database_url == 'sqlite://'
    assert mock_settings.jwt_secret_key == 'test-jwt-secret'
    assert mock_settings.jwt_algorithm == 'HS256'
    assert mock_settings.access_token_expire_minutes == 30
    assert mock_settings.refresh_token_expire_days == 7

def test_test_user_data_fixture(test_user_data):
    assert test_user_data['email'] == 'test@example.com'
    assert test_user_data['password'] == 'testpassword123'
    assert test_user_data['hashed_password'].startswith('$2b$')

def test_sample_tokens_fixture(sample_tokens):
    assert 'access_token' in sample_tokens
    assert 'refresh_token' in sample_tokens
    assert sample_tokens['access_token'].startswith('eyJ')
    assert sample_tokens['refresh_token'].startswith('eyJ')
    assert sample_tokens['access_token'] != sample_tokens['refresh_token']

def test_db_session_isolation(db_session):
    user1 = User(email='user1@test.com', hashed_password='hash1')
    db_session.add(user1)
    db_session.commit()
    assert user1.id == 1
    user2 = User(email='user2@test.com', hashed_password='hash2')
    db_session.add(user2)
    db_session.commit()
    assert user2.id == 2
    assert user1.id != user2.id

def test_mock_settings_with_get_settings(mock_settings):
    with patch('src.config.get_settings', return_value=mock_settings):
        settings = get_settings()
        assert settings is mock_settings
        assert settings.database_url == 'sqlite://'

def test_fixtures_can_be_used_together(db_session, test_user_data, sample_tokens):
    user = User(email=test_user_data['email'], hashed_password=test_user_data['hashed_password'])
    db_session.add(user)
    db_session.commit()
    assert user.email == test_user_data['email']
    assert user.hashed_password == test_user_data['hashed_password']
    assert sample_tokens['access_token'] != sample_tokens['refresh_token']