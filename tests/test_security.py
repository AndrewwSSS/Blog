import time

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.security import (
    generate_email_verification_token,
    get_password_hash,
    verify_verification_token,
)
from app.pubsub.services import mail_service
from app.schemas.user import UserInDB, UserLoginRequest
from app.services.user_service import UserService


def make_user(**overrides) -> UserInDB:
    data = {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com",
        "post_auto_reply": False,
        "reply_after": 1.0,
        "hashed_password": get_password_hash("correct-password"),
        "welcome_email_sent": False,
        "is_active": True,
        "is_admin": False,
    }
    data.update(overrides)
    return UserInDB(**data)


class FakeUserRepository:
    def __init__(self, user: UserInDB | None) -> None:
        self.user = user

    async def get_by_username(self, username: str) -> UserInDB | None:
        if self.user and self.user.username == username:
            return self.user
        return None


def test_verification_token_roundtrip():
    token = generate_email_verification_token("alice@example.com")

    assert verify_verification_token(token) == "alice@example.com"


def test_verification_token_expires(monkeypatch):
    token = generate_email_verification_token("alice@example.com")
    expired_at = time.time() + settings.EMAIL_TOKEN_EXPIRE_HOURS * 3600 + 1
    monkeypatch.setattr("itsdangerous.timed.time.time", lambda: expired_at)

    assert verify_verification_token(token) is None


def test_verification_token_rejects_tampering():
    token = generate_email_verification_token("alice@example.com")

    assert verify_verification_token(token + "x") is None


@pytest.mark.parametrize(
    "username, password",
    [
        ("unknown", "correct-password"),
        ("alice", "wrong-password"),
    ],
)
async def test_authenticate_hides_whether_user_exists(username, password):
    service = UserService(FakeUserRepository(make_user()), outbox_repository=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.authenticate(UserLoginRequest(username=username, password=password))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect username or password"


async def test_authenticate_returns_user_for_correct_password():
    user = make_user()
    service = UserService(FakeUserRepository(user), outbox_repository=None)

    result = await service.authenticate(
        UserLoginRequest(username="alice", password="correct-password")
    )

    assert result == user


def test_email_html_escapes_username():
    service = mail_service.EmailService(make_user(username='<img src=x onerror="alert(1)">'))

    welcome = service._generate_welcome_email_html()
    verification = service._generate_verification_email_html("http://x/?a=1&b=2")

    assert "<img" not in welcome
    assert "&lt;img" in welcome
    assert "<img" not in verification
    assert 'href="http://x/?a=1&amp;b=2"' in verification
