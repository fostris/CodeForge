import pytest
from unittest.mock import patch
from src.config import Config, get_jwt_private_key
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidKey

# Mock the config module for testing
@pytest.fixture
def mock_config():
    with patch('src.config.Config') as MockConfig:
        MockConfig.get_logger.return_value = "mock_logger"
        MockConfig.MODEL_TIERS = {}
        yield MockConfig

@patch('builtins.open')
def test_get_jwt_private_key_success(mock_open, mock_config):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )

    mock_open.return_value.read.return_value = pem

    config_instance = mock_config()
    config_instance.JWT_PRIVATE_KEY_PATH = 'test_key.pem'
    
    result = get_jwt_private_key(config_instance)
    
    assert isinstance(result, rsa.RSAPrivateKey)

@patch('builtins.open')
def test_get_jwt_private_key_file_not_found(mock_open, mock_config):
    mock_open.side_effect = FileNotFoundError("No such file or directory: 'nonexistent.pem'")

    config_instance = mock_config()
    config_instance.JWT_PRIVATE_KEY_PATH = 'nonexistent.pem'
    
    with pytest.raises(FileNotFoundError) as exc_info:
        get_jwt_private_key(config_instance)
        
    assert str(exc_info.value) == "FileNotFoundError: No such file or directory: 'nonexistent.pem'"

@patch('builtins.open')
def test_get_jwt_private_key_invalid_key(mock_open, mock_config):
    mock_open.return_value.read.return_value = b"invalid-key-data"
    
    config_instance = mock_config()
    config_instance.JWT_PRIVATE_KEY_PATH = 'test_key.pem'
    
    with pytest.raises(InvalidKey) as exc_info:
        get_jwt_private_key(config_instance)
        
    assert str(exc_info.value).startswith("Invalid key")