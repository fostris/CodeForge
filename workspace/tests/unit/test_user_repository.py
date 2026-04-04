import pytest
import uuid
from unittest.mock import Mock, create_autospec
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.auth.repositories import UserRepositoryImpl
from src.auth.models import User, UserCreate
from src.auth.exceptions import DuplicateEmailError


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    return create_autospec(Session, instance=True)


@pytest.fixture
def user_repository(mock_session):
    """Create UserRepositoryImpl with mock session."""
    return UserRepositoryImpl(mock_session)


@pytest.fixture
def sample_user_create():
    """Create a sample UserCreate object."""
    return UserCreate(email="test@example.com", password="Password123")


@pytest.fixture
def sample_user():
    """Create a sample User object."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password_123"
    )


class TestUserRepositoryImpl:
    """Test UserRepositoryImpl methods."""
    
    def test_create_success(self, user_repository, mock_session, sample_user_create):
        """Test successful user creation."""
        # Mock exists_by_email to return False
        mock_session.execute.return_value.first.return_value = None
        
        # Mock the flush to simulate database operation
        mock_session.add = Mock()
        mock_session.flush = Mock()
        
        # Create user
        hashed_password = "hashed_password_123"
        result = user_repository.create(sample_user_create, hashed_password)
        
        # Verify user was created with correct data
        assert result.email == sample_user_create.email
        assert result.hashed_password == hashed_password
        assert mock_session.add.called
        assert mock_session.flush.called
    
    def test_create_duplicate_email(self, user_repository, mock_session, sample_user_create):
        """Test user creation with duplicate email raises DuplicateEmailError."""
        # Mock exists_by_email to return True
        mock_session.execute.return_value.first.return_value = (uuid.uuid4(),)
        
        # Attempt to create user with duplicate email
        hashed_password = "hashed_password_123"
        
        with pytest.raises(DuplicateEmailError):
            user_repository.create(sample_user_create, hashed_password)
        
        # Verify session.add was not called
        assert not mock_session.add.called
    
    def test_get_by_id_found(self, user_repository, mock_session, sample_user):
        """Test get_by_id when user exists."""
        # Mock the execute to return the sample user
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_user
        
        result = user_repository.get_by_id(sample_user.id)
        
        assert result == sample_user
        # Verify the query was constructed correctly
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, type(select(User)))
    
    def test_get_by_id_not_found(self, user_repository, mock_session):
        """Test get_by_id when user doesn't exist."""
        # Mock the execute to return None
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        user_id = uuid.uuid4()
        result = user_repository.get_by_id(user_id)
        
        assert result is None
        # Verify the query was constructed correctly
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, type(select(User)))
    
    def test_get_by_email_found(self, user_repository, mock_session, sample_user):
        """Test get_by_email when user exists."""
        # Mock the execute to return the sample user
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_user
        
        result = user_repository.get_by_email(sample_user.email)
        
        assert result == sample_user
        # Verify the query was constructed correctly
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, type(select(User)))
    
    def test_get_by_email_not_found(self, user_repository, mock_session):
        """Test get_by_email when user doesn't exist."""
        # Mock the execute to return None
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        
        email = "nonexistent@example.com"
        result = user_repository.get_by_email(email)
        
        assert result is None
        # Verify the query was constructed correctly
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, type(select(User)))
    
    def test_exists_by_email_true(self, user_repository, mock_session):
        """Test exists_by_email returns True when user exists."""
        # Mock the execute to return a result (user exists)
        mock_session.execute.return_value.first.return_value = (uuid.uuid4(),)
        
        email = "existing@example.com"
        result = user_repository.exists_by_email(email)
        
        assert result is True
        # Verify the query was constructed correctly
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, type(select(User.id)))
    
    def test_exists_by_email_false(self, user_repository, mock_session):
        """Test exists_by_email returns False when user doesn't exist."""
        # Mock the execute to return None (user doesn't exist)
        mock_session.execute.return_value.first.return_value = None
        
        email = "nonexistent@example.com"
        result = user_repository.exists_by_email(email)
        
        assert result is False
        # Verify the query was constructed correctly
        call_args = mock_session.execute.call_args[0][0]
        assert isinstance(call_args, type(select(User.id)))