import re
from typing import Optional


class ValidationError(Exception):
    """Exception raised for validation errors."""
    pass


class EmailValidator:
    """Email format validator."""
    
    # Simplified regex for basic email format validation
    # This follows a common pattern: local-part@domain
    # Allows letters, digits, dots, hyphens, underscores in local part
    # Domain must have at least one dot (e.g., example.com)
    # This is a pragmatic validator, not RFC 5322 compliant
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    def validate(self, email: Optional[str]) -> None:
        """
        Validate email format.
        
        Args:
            email: The email address to validate.
            
        Raises:
            ValidationError: If email is None, empty, or doesn't match format.
        """
        if email is None:
            raise ValidationError("Email cannot be None")
        
        if not isinstance(email, str):
            raise ValidationError("Email must be a string")
        
        email = email.strip()
        
        if not email:
            raise ValidationError("Email cannot be empty")
        
        if not self.EMAIL_REGEX.match(email):
            raise ValidationError("Invalid email format")