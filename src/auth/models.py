from datetime import datetime


def get_current_timestamp() -> datetime:
    return datetime.utcnow()


class User:
    pass


class RefreshToken:
    def __init__(
        self,
        token_hash: str | None = None,
        user_id: int | None = None,
        user: User | None = None,
        expires_at: datetime | None = None,
        revoked: bool = False,
        id: int | None = None,
    ) -> None:
        self.id = id
        self.token_hash = token_hash
        self.user_id = user_id
        self.user = user
        self.expires_at = expires_at
        self.created_at = get_current_timestamp()
        self.revoked = revoked

    def __repr__(self) -> str:
        return f"<RefreshToken {self.id}>"