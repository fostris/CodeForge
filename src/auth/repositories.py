import hashlib
from datetime import datetime, timedelta
from typing import Optional

from src.auth.models import RefreshToken


class RefreshTokenRepository:
    @staticmethod
    def now() -> datetime:
        return datetime.now()

    def create(self, token_value: str, expires_in: timedelta) -> None:
        token_hash = hashlib.sha256(token_value.encode()).hexdigest()
        RefreshToken.objects.create(
            token_hash=token_hash,
            expires_at=self.now() + expires_in,
            revoked=False,
        )

    @staticmethod
    def get_valid_token(token_hash: str) -> Optional[RefreshToken]:
        try:
            token = RefreshToken.objects.get(token_hash=token_hash, revoked=False)
            if RefreshTokenRepository.now() < token.expires_at:
                return token
            return None
        except RefreshToken.DoesNotExist:
            return None

    @staticmethod
    def revoke(token_hash: str) -> None:
        RefreshToken.objects.filter(token_hash=token_hash).update(revoked=True)

    @staticmethod
    def revoke_all_for_user(user_id: int) -> int:
        return RefreshToken.objects.filter(user_id=user_id).update(revoked=True)