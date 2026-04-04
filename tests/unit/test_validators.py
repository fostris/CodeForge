import pytest
from src.utils.validators import validate_password_strength, ValidationResult

def test_validate_password_strength_success():
    password = "Abc123!@#"
    result = validate_password_strength(password)
    assert isinstance(result, ValidationResult)
    assert result.score == 5
    assert not result.errors

def test_validate_password_strength_length_error():
    password = "abc"
    result = validate_password_strength(password)
    assert isinstance(result, ValidationResult)
    assert result.score == 0
    assert "Password must be at least 8 characters long" in result.errors

def test_validate_password_strength_uppercase_error():
    password = "abc123!@#"
    result = validate_password_strength(password)
    assert isinstance(result, ValidationResult)
    assert result.score == 0
    assert "Password must contain an uppercase letter" in result.errors

def test_validate_password_strength_lowercase_error():
    password = "ABC123!@#"
    result = validate_password_strength(password)
    assert isinstance(result, ValidationResult)
    assert result.score == 0
    assert "Password must contain a lowercase letter" in result.errors

def test_validate_password_strength_digit_error():
    password = "Abc!@#"
    result = validate_password_strength(password)
    assert isinstance(result, ValidationResult)
    assert result.score == 0
    assert "Password must contain a digit" in result.errors

def test_validate_password_strength_special_char_error():
    password = "Abc123"
    result = validate_password_strength(password)
    assert isinstance(result, ValidationResult)
    assert result.score == 0
    assert "Password must contain a special character" in result.errors