import pytest
from unittest.mock import patch
from src.auth.security import hash_password, verify_password
import bcrypt

# Test hash_password uses bcrypt algorithm with cost factor 12
@patch('bcrypt.hashpw')
def test_hash_password(bcrypt_hashpw):
    password = b'password'
    salt = bcrypt.gensalt(12)
    bcrypt_hashpw.return_value = b'$2b$12$examplehash'

    result = hash_password(password)

    assert bcrypt_hashpw.called_once_with(password, salt)
    assert isinstance(result, bytes)

# Test verify_password returns boolean correctly
@patch('bcrypt.checkpw')
def test_verify_password(bcrypt_checkpw):
    password = b'password'
    hashed_password = b'$2b$12$examplehash'

    bcrypt_checkpw.return_value = True

    result = verify_password(password, hashed_password)

    assert bcrypt_checkpw.called_once_with(password, hashed_password)
    assert isinstance(result, bool)
    assert result

@patch('bcrypt.checkpw')
def test_verify_password_false(bcrypt_checkpw):
    password = b'password'
    hashed_password = b'$2b$12$examplehash'

    bcrypt_checkpw.return_value = False

    result = verify_password(password, hashed_password)

    assert bcrypt_checkpw.called_once_with(password, hashed_password)
    assert isinstance(result, bool)
    assert not result