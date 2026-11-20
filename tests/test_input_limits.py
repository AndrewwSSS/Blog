from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_password_hash
from app.main import app
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    LOGIN_USERNAME_MAX_LENGTH,
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    UserInDB,
)
from app.services import user_service

REGISTER_URL = "/api/v1/users/register"
LOGIN_URL = "/api/v1/users/token"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def registration(username: str = "alice", password: str = "a" * PASSWORD_MIN_LENGTH) -> dict:
    return {"username": username, "email": f"{username}@example.com", "password": password}


@pytest.mark.parametrize(
    "password, expected",
    [
        ("a" * (PASSWORD_MIN_LENGTH - 1), 422),
        ("a" * PASSWORD_MIN_LENGTH, 201),
        ("a" * PASSWORD_MAX_LENGTH, 201),
        ("a" * (PASSWORD_MAX_LENGTH + 1), 422),
    ],
)
async def test_register_password_length_limits(client: AsyncClient, password: str, expected: int):
    response = await client.post(REGISTER_URL, json=registration(password=password))

    assert response.status_code == expected


@pytest.mark.parametrize(
    "username, expected",
    [
        ("a" * (USERNAME_MIN_LENGTH - 1), 422),
        ("a" * USERNAME_MIN_LENGTH, 201),
        ("a" * USERNAME_MAX_LENGTH, 201),
        ("a" * (USERNAME_MAX_LENGTH + 1), 422),
    ],
)
async def test_register_username_length_limits(client: AsyncClient, username: str, expected: int):
    response = await client.post(REGISTER_URL, json=registration(username=username))

    assert response.status_code == expected


async def test_huge_password_is_rejected_before_hashing(client: AsyncClient, monkeypatch):
    hashed = []
    monkeypatch.setattr(user_service, "get_password_hash", lambda pw: hashed.append(pw) or "x")

    response = await client.post(REGISTER_URL, json=registration(password="a" * 1_000_000))

    assert response.status_code == 422
    assert hashed == []


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "alice", "password": "a" * (PASSWORD_MAX_LENGTH + 1)},
        {"username": "a" * (LOGIN_USERNAME_MAX_LENGTH + 1), "password": "password123"},
    ],
)
async def test_login_rejects_too_long_input(client: AsyncClient, payload: dict):
    response = await client.post(LOGIN_URL, json=payload)

    assert response.status_code == 422


async def test_existing_account_with_short_password_can_still_log_in(
    client: AsyncClient, test_user: UserInDB, session
):
    await UserRepository(session).update_by_id(
        test_user.id, hashed_password=get_password_hash("pw"), is_active=True
    )
    await session.commit()

    response = await client.post(LOGIN_URL, json={"username": test_user.username, "password": "pw"})

    assert response.status_code == 200
    assert len(test_user.username) > USERNAME_MAX_LENGTH
