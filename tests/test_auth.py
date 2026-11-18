from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.utils import create_access_token, create_refresh_token
from app.main import app
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserInDB

ME_URL = "/api/v1/users/me"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def active_user(test_user: UserInDB, session: AsyncSession) -> UserInDB:
    await UserRepository(session).update_by_id(test_user.id, is_active=True)
    return test_user


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_valid_access_token_returns_user(client: AsyncClient, active_user: UserInDB):
    token = create_access_token({"user_id": active_user.id})

    response = await client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 200
    assert response.json()["username"] == active_user.username


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-jwt"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
    ],
)
async def test_missing_or_malformed_token_is_401(client: AsyncClient, headers):
    response = await client.get(ME_URL, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_refresh_token_is_rejected(client: AsyncClient, active_user: UserInDB):
    token = create_refresh_token({"user_id": active_user.id})

    response = await client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token type"


async def test_token_for_unknown_user_is_401(client: AsyncClient):
    token = create_access_token({"user_id": 999})

    response = await client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 401


async def test_inactive_user_is_401(client: AsyncClient, test_user: UserInDB):
    token = create_access_token({"user_id": test_user.id})

    response = await client.get(ME_URL, headers=bearer(token))

    assert response.status_code == 401
    assert response.json()["detail"] == "Inactive user"


def test_openapi_uses_http_bearer():
    schemes = app.openapi()["components"]["securitySchemes"]

    assert schemes == {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "description": "Access token from POST /api/v1/users/token",
        }
    }
