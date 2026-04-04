import os
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from passlib.context import CryptContext
import logging

class ModelTierConfig(BaseModel):
    max_requests_per_day: int = Field(default=100)
    cost_per_request: float = Field(default=0.01)

class Settings(BaseSettings):
    # Database
    database_url: str = Field(default="sqlite:///./test.db")
    
    # JWT
    jwt_secret: str = Field(default="default_secret_key_change_in_production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    
    # Bcrypt
    bcrypt_cost: int = Field(default=12)
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(default=60)
    rate_limit_window_minutes: int = Field(default=1)
    
    # Model tiers configuration
    model_tiers: Dict[str, ModelTierConfig] = Field(
        default={
            "free": ModelTierConfig(max_requests_per_day=100, cost_per_request=0.0),
            "basic": ModelTierConfig(max_requests_per_day=1000, cost_per_request=0.01),
            "pro": ModelTierConfig(max_requests_per_day=10000, cost_per_request=0.005),
        }
    )
    
    # Logging
    log_level: str = Field(default="INFO")
    
    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("database_url cannot be empty")
        return v
    
    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("jwt_secret must be at least 16 characters long")
        return v
    
    @field_validator("bcrypt_cost")
    @classmethod
    def validate_bcrypt_cost(cls, v: int) -> int:
        if v < 4 or v > 20:
            raise ValueError("bcrypt_cost must be between 4 and 20")
        return v
    
    @field_validator("rate_limit_requests_per_minute")
    @classmethod
    def validate_rate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("rate_limit_requests_per_minute must be positive")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v
    
    class Config:
        env_prefix = "APP_"
        case_sensitive = False

_settings_instance: Optional[Settings] = None

def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Only add handler if logger doesn't have any handlers yet
    if not logger.handlers:
        settings = get_settings()
        
        # Convert string level to numeric level
        level = getattr(logging, settings.log_level)
        logger.setLevel(level)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

# CryptContext for password hashing - initialize with default cost first
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

# Update rounds when settings are loaded
def _update_pwd_context():
    settings = get_settings()
    pwd_context.bcrypt__rounds = settings.bcrypt_cost

# Initialize with correct rounds
_update_pwd_context()