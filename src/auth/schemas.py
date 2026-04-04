from pydantic import BaseModel, Field, ConfigDict


class RefreshRequest(BaseModel):
    refresh_token: str = Field(...)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: str
    is_active: bool

    @property
    def password(self) -> None:
        raise AttributeError("password field is not accessible")