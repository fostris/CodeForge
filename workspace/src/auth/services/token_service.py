import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from src.auth.exceptions import ExpiredTokenError, InvalidTokenError
from src.auth.models import TokenPair
from src.config import get_settings

settings = get_settings()


class TokenService:
    """Service for JWT token operations."""

    def __init__(self) -> None:
        self.secret_key = settings.jwt_secret
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days

    def create_access_token(self, user_id: str, email: str) -> str:
        """Create an access token with user_id and email claims."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.access_token_expire_minutes
        )
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token with user_id claim."""
        expire = datetime.now(timezone.utc) + timedelta(
            days=self.refresh_token_expire_days
        )
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(self, user_id: str, email: str) -> TokenPair:
        """Create both access and refresh tokens."""
        access_token = self.create_access_token(user_id, email)
        refresh_token = self.create_refresh_token(user_id)
        return TokenPair(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    def validate_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Validate a token and return its payload.
        
        Raises:
            InvalidTokenError: If token is invalid or malformed
            ExpiredTokenError: If token has expired
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": True}
            )
            
            # Check token type if specified
            if token_type and payload.get("type") != token_type:
                raise InvalidTokenError("Invalid token type")
                
            return payload
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenError()
        except jwt.InvalidTokenError:
            raise InvalidTokenError()

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode a token without validation.
        
        Returns:
            The decoded token payload (even if expired)
        """
        try:
            return jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False}
            )
        except jwt.InvalidTokenError:
            raise InvalidTokenError()