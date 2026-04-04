import pytest
from src.auth.exceptions import (
    AuthException,
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenError,
    ExpiredTokenError,
    DuplicateEmailError,
    RateLimitExceededError,
    ValidationException,
)


class TestAuthException:
    """Test the base AuthException class."""
    
    def test_base_exception_creation(self):
        """Test that AuthException can be created with custom status and detail."""
        exception = AuthException(status_code=400, detail="Test error")
        
        assert exception.status_code == 400
        assert exception.detail == "Test error"
        assert str(exception) == "Test error"
    
    def test_base_exception_with_args(self):
        """Test that AuthException passes args to parent Exception."""
        exception = AuthException(400, "Test", "arg1", "arg2")
        
        assert exception.args == ("Test", "arg1", "arg2")
        assert exception.status_code == 400
        assert exception.detail == "Test"


class TestAuthenticationError:
    """Test AuthenticationError exception."""
    
    def test_default_values(self):
        """Test AuthenticationError with default values."""
        exception = AuthenticationError()
        
        assert exception.status_code == 401
        assert exception.detail == "Authentication failed"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test AuthenticationError with custom detail message."""
        exception = AuthenticationError(detail="Custom auth failure")
        
        assert exception.status_code == 401
        assert exception.detail == "Custom auth failure"


class TestInvalidCredentialsError:
    """Test InvalidCredentialsError exception."""
    
    def test_default_values(self):
        """Test InvalidCredentialsError with default values."""
        exception = InvalidCredentialsError()
        
        assert exception.status_code == 401
        assert exception.detail == "Invalid credentials"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test InvalidCredentialsError with custom detail message."""
        exception = InvalidCredentialsError(detail="Wrong password")
        
        assert exception.status_code == 401
        assert exception.detail == "Wrong password"


class TestInvalidTokenError:
    """Test InvalidTokenError exception."""
    
    def test_default_values(self):
        """Test InvalidTokenError with default values."""
        exception = InvalidTokenError()
        
        assert exception.status_code == 401
        assert exception.detail == "Invalid token"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test InvalidTokenError with custom detail message."""
        exception = InvalidTokenError(detail="Malformed JWT")
        
        assert exception.status_code == 401
        assert exception.detail == "Malformed JWT"


class TestExpiredTokenError:
    """Test ExpiredTokenError exception."""
    
    def test_default_values(self):
        """Test ExpiredTokenError with default values."""
        exception = ExpiredTokenError()
        
        assert exception.status_code == 401
        assert exception.detail == "Token has expired"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test ExpiredTokenError with custom detail message."""
        exception = ExpiredTokenError(detail="Refresh token expired")
        
        assert exception.status_code == 401
        assert exception.detail == "Refresh token expired"


class TestDuplicateEmailError:
    """Test DuplicateEmailError exception."""
    
    def test_default_values(self):
        """Test DuplicateEmailError with default values."""
        exception = DuplicateEmailError()
        
        assert exception.status_code == 409
        assert exception.detail == "Email already registered"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test DuplicateEmailError with custom detail message."""
        exception = DuplicateEmailError(detail="user@example.com already exists")
        
        assert exception.status_code == 409
        assert exception.detail == "user@example.com already exists"


class TestRateLimitExceededError:
    """Test RateLimitExceededError exception."""
    
    def test_default_values(self):
        """Test RateLimitExceededError with default values."""
        exception = RateLimitExceededError()
        
        assert exception.status_code == 429
        assert exception.detail == "Rate limit exceeded"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test RateLimitExceededError with custom detail message."""
        exception = RateLimitExceededError(detail="Too many login attempts")
        
        assert exception.status_code == 429
        assert exception.detail == "Too many login attempts"


class TestValidationException:
    """Test ValidationException exception."""
    
    def test_default_values(self):
        """Test ValidationException with default values."""
        exception = ValidationException()
        
        assert exception.status_code == 422
        assert exception.detail == "Validation error"
        assert isinstance(exception, AuthException)
    
    def test_custom_detail(self):
        """Test ValidationException with custom detail message."""
        exception = ValidationException(detail="Email format is invalid")
        
        assert exception.status_code == 422
        assert exception.detail == "Email format is invalid"


class TestExceptionHierarchy:
    """Test that the exception hierarchy is correct."""
    
    def test_inheritance_chain(self):
        """Test that all exceptions inherit from AuthException."""
        exceptions = [
            AuthenticationError,
            InvalidCredentialsError,
            InvalidTokenError,
            ExpiredTokenError,
            DuplicateEmailError,
            RateLimitExceededError,
            ValidationException,
        ]
        
        for exc_class in exceptions:
            exc_instance = exc_class()
            assert isinstance(exc_instance, AuthException)