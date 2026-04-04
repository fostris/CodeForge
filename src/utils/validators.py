import re
from typing import List


class ValidationResult:
    """Result of password validation."""

    def __init__(self) -> None:
        self.score: int = 0
        self.errors: List[str] = []


def validate_password_strength(password: str) -> ValidationResult:
    """Validate password strength based on certain criteria.

    Args:
        password: The password to validate.

    Returns:
        ValidationResult containing the validation score and any errors.
    """
    result = ValidationResult()

    # Check length
    if len(password) < 8:
        result.errors.append("Password must be at least 8 characters long")

    # Check for uppercase letter
    if not re.search(r"[A-Z]", password):
        result.errors.append("Password must contain an uppercase letter")

    # Check for lowercase letter
    if not re.search(r"[a-z]", password):
        result.errors.append("Password must contain a lowercase letter")

    # Check for digit
    if not re.search(r"\d", password):
        result.errors.append("Password must contain a digit")

    # Check for special character
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        result.errors.append("Password must contain a special character")

    # Set score based on validation result
    if not result.errors:
        result.score = 5
    else:
        result.score = 0

    return result