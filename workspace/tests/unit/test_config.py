import pytest
from unittest.mock import patch
import logging
from src.config import Settings, get_settings, get_logger, ModelTierConfig, pwd_context

def test_settings_default_values():
    """Test that Settings loads with default values when no env vars are set."""
    settings = Settings()
    
    assert settings.database_url == "sqlite:///./test.db"
    assert settings.jwt_secret == "default_secret_key_change_in_production"
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_expire_minutes == 30
    assert settings.bcrypt_cost == 12
    assert settings.rate_limit_requests_per_minute == 60
    assert settings.rate_limit_window_minutes == 1
    assert settings.log_level == "INFO"
    
    assert "free" in settings.model_tiers
    assert settings.model_tiers["free"].max_requests_per_day == 100
    assert settings.model_tiers["free"].cost_per_request == 0.0
    assert "basic" in settings.model_tiers
    assert "pro" in settings.model_tiers

def test_settings_from_environment():
    """Test that Settings loads from environment variables."""
    env_vars = {
        "APP_DATABASE_URL": "postgresql://user:pass@localhost/db",
        "APP_JWT_SECRET": "super_secret_key_1234567890",
        "APP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "60",
        "APP_BCRYPT_COST": "8",
        "APP_RATE_LIMIT_REQUESTS_PER_MINUTE": "100",
        "APP_LOG_LEVEL": "DEBUG",
    }
    
    with patch.dict("os.environ", env_vars):
        settings = Settings()
        
        assert settings.database_url == "postgresql://user:pass@localhost/db"
        assert settings.jwt_secret == "super_secret_key_1234567890"
        assert settings.jwt_access_token_expire_minutes == 60
        assert settings.bcrypt_cost == 8
        assert settings.rate_limit_requests_per_minute == 100
        assert settings.log_level == "DEBUG"

def test_settings_validation_database_url():
    """Test validation for database_url."""
    with pytest.raises(ValueError):
        Settings(database_url="")

def test_settings_validation_jwt_secret():
    """Test validation for jwt_secret."""
    with pytest.raises(ValueError):
        Settings(jwt_secret="short")
    
    # Valid secret
    settings = Settings(jwt_secret="long_secret_key_1234567890")
    assert settings.jwt_secret == "long_secret_key_1234567890"

def test_settings_validation_bcrypt_cost():
    """Test validation for bcrypt_cost."""
    with pytest.raises(ValueError):
        Settings(bcrypt_cost=3)
    
    with pytest.raises(ValueError):
        Settings(bcrypt_cost=21)
    
    # Valid costs
    settings = Settings(bcrypt_cost=4)
    assert settings.bcrypt_cost == 4
    
    settings = Settings(bcrypt_cost=20)
    assert settings.bcrypt_cost == 20

def test_settings_validation_rate_limit():
    """Test validation for rate_limit_requests_per_minute."""
    with pytest.raises(ValueError):
        Settings(rate_limit_requests_per_minute=0)
    
    with pytest.raises(ValueError):
        Settings(rate_limit_requests_per_minute=-5)
    
    # Valid rate limit
    settings = Settings(rate_limit_requests_per_minute=1)
    assert settings.rate_limit_requests_per_minute == 1

def test_settings_validation_log_level():
    """Test validation for log_level."""
    with pytest.raises(ValueError):
        Settings(log_level="INVALID")
    
    # Valid levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        settings = Settings(log_level=level)
        assert settings.log_level == level

def test_get_settings_singleton():
    """Test that get_settings returns a singleton instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2
    
    # Verify it's the same object
    assert settings1.database_url == settings2.database_url

def test_get_logger():
    """Test get_logger returns a configured logger."""
    settings = get_settings()
    
    logger = get_logger("test_logger")
    
    assert logger.name == "test_logger"
    assert logger.level == logging.getLevelName(settings.log_level)
    assert len(logger.handlers) > 0
    
    # Test with different log level
    with patch.dict("os.environ", {"APP_LOG_LEVEL": "DEBUG"}):
        # Force reload of settings
        from src.config import _settings_instance
        _settings_instance = None
        
        # Clear existing handlers to ensure fresh logger
        test_logger = logging.getLogger("test_logger2")
        test_logger.handlers.clear()
        
        # Also clear the logger from the logging module's cache
        logging.Logger.manager.loggerDict.pop("test_logger2", None)
        
        logger2 = get_logger("test_logger2")
        assert logger2.level == logging.DEBUG

def test_model_tier_config():
    """Test ModelTierConfig model."""
    config = ModelTierConfig(max_requests_per_day=500, cost_per_request=0.02)
    
    assert config.max_requests_per_day == 500
    assert config.cost_per_request == 0.02
    
    # Test defaults
    config_default = ModelTierConfig()
    assert config_default.max_requests_per_day == 100
    assert config_default.cost_per_request == 0.01

def test_pwd_context_initialization():
    """Test that CryptContext is initialized with bcrypt rounds from settings."""
    settings = get_settings()
    
    # pwd_context should be initialized with the bcrypt cost from settings
    # We can't directly check the rounds, but we can verify the context exists
    assert pwd_context is not None
    assert "bcrypt" in pwd_context.schemes()

def test_settings_case_insensitive_env():
    """Test that environment variables are case-insensitive."""
    env_vars = {
        "app_database_url": "sqlite:///case_test.db",  # lowercase prefix
    }
    
    with patch.dict("os.environ", env_vars):
        settings = Settings()
        assert settings.database_url == "sqlite:///case_test.db"

def test_settings_env_prefix():
    """Test that only prefixed environment variables are loaded."""
    env_vars = {
        "APP_DATABASE_URL": "sqlite:///prefixed.db",
        "DATABASE_URL": "sqlite:///unprefixed.db",  # Should be ignored
    }
    
    with patch.dict("os.environ", env_vars):
        settings = Settings()
        assert settings.database_url == "sqlite:///prefixed.db"