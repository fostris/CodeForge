import pytest
from pydantic import ValidationError
from src.auth.schemas import RefreshRequest, UserResponse

def test_refresh_request():
    data = {"refresh_token": "abc123"}
    request = RefreshRequest(**data)
    assert request.refresh_token == "abc123"

    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token=None)

    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="")

def test_user_response():
    data = {
        "id": 1,
        "email": "user@example.com",
        "created_at": "2023-04-01T00:00:00Z",
        "is_active": True
    }
    response = UserResponse(**data)
    assert response.id == 1
    assert response.email == "user@example.com"
    assert response.created_at == "2023-04-01T00:00:00Z"
    assert response.is_active is True

    # Test excludes sensitive fields
    with pytest.raises(AttributeError):
        _ = response.password