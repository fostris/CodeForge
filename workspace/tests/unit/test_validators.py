from pydantic import ValidationError
import pytest
from utils.validators import EmailValidator, ValidationError


class TestEmailValidator:
    """Test suite for EmailValidator."""
    
    @pytest.fixture
    def validator(self):
        """Return a fresh EmailValidator instance."""
        return EmailValidator()
    
    def test_valid_emails(self, validator):
        """Test that valid email formats pass validation."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@example.org",
            "123456@example.com",
            "user-name@example-domain.com",
            "u@example.com",  # Short local part
            "user@example.co",  # Short domain extension
        ]
        
        for email in valid_emails:
            # Should not raise any exception
            validator.validate(email)
    
    def test_invalid_emails(self, validator):
        """Test that invalid email formats raise ValidationError."""
        invalid_cases = [
            (None, "None email"),
            ("", "Empty string"),
            ("   ", "Whitespace only"),
            ("plainaddress", "Missing @"),
            ("@example.com", "Missing local part"),
            ("user@", "Missing domain"),
            ("user@example", "Missing domain extension"),
            ("user@.com", "Domain starts with dot"),
            ("user@example..com", "Double dot in domain"),
            ("user@example.c", "Single char domain extension"),
            ("user name@example.com", "Space in local part"),
            ("user@example com", "Space in domain"),
            ("user@-example.com", "Domain starts with hyphen"),
            ("user@example-.com", "Domain ends with hyphen"),
            ("<user@example.com>", "Angle brackets"),
            ("user@example_com", "Underscore in domain"),
            ("user@123.456.789.123", "IP address format"),
        ]
        
        for email, description in invalid_cases:
            with pytest.raises(ValidationError):
                validator.validate(email)
    
    def test_non_string_input(self, validator):
        """Test that non-string inputs raise ValidationError."""
        non_strings = [
            123,
            123.45,
            True,
            False,
            [],
            {},
            object(),
        ]
        
        for value in non_strings:
            with pytest.raises(ValidationError):
                validator.validate(value)
    
    def test_email_with_whitespace_padding(self, validator):
        """Test that emails with surrounding whitespace are properly trimmed."""
        # Valid emails with whitespace should pass after trimming
        padded_valid = [
            "  user@example.com  ",
            "\tuser@example.com\n",
            " user@example.com ",
        ]
        
        for email in padded_valid:
            validator.validate(email)
        
        # Invalid emails with whitespace should still fail
        padded_invalid = [
            "  @example.com  ",
            "  user@  ",
        ]
        
        for email in padded_invalid:
            with pytest.raises(ValidationError):
                validator.validate(email)
    
    def test_validation_error_type(self, validator):
        """Test that the correct exception type is raised."""
        with pytest.raises(ValidationError) as exc_info:
            validator.validate("invalid-email")
        
        assert isinstance(exc_info.value, ValidationError)
        assert issubclass(ValidationError, Exception)