import pytest
from argon2 import PasswordHasher
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    dummy_verify_password,
    get_password_hash,
    password_needs_rehash,
    verify_password,
)
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserInDB, UserLoginRequest
from app.services.user_service import UserService

# Hashes created by the previous passlib CryptContext(schemes=["bcrypt"]).
PASSLIB_HASH = "$2b$12$82.QTrUqrJlqjXSCmGDnyO2D04vvKLYBnT95wKG/vxeybklTA/BYO"
PASSLIB_HASH_OF_80_A = "$2b$12$zZGE66c8m.SYoUzIsaLalO/VKllz0vR/WDLaWchPB1ezi86Sn0uJy"


def test_new_hashes_are_argon2id():
    hashed = get_password_hash("correct-password")

    assert hashed.startswith("$argon2id$")
    assert verify_password("correct-password", hashed)
    assert not verify_password("wrong-password", hashed)
    assert not password_needs_rehash(hashed)


def test_long_and_non_ascii_passwords_are_not_truncated():
    hashed = get_password_hash("a" * 100 + "пароль-密码")

    assert verify_password("a" * 100 + "пароль-密码", hashed)
    assert not verify_password("a" * 100, hashed)


def test_legacy_passlib_hashes_still_verify_and_need_rehash():
    assert verify_password("correct-password", PASSLIB_HASH)
    assert not verify_password("wrong-password", PASSLIB_HASH)
    assert password_needs_rehash(PASSLIB_HASH)


def test_legacy_long_passwords_keep_passlib_truncation():
    assert verify_password("a" * 80, PASSLIB_HASH_OF_80_A)
    assert verify_password("a" * 72, PASSLIB_HASH_OF_80_A)


def test_argon2_hash_with_old_parameters_needs_rehash():
    weak_hash = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("pw")

    assert verify_password("pw", weak_hash)
    assert password_needs_rehash(weak_hash)


@pytest.mark.parametrize(
    "hashed",
    [
        "not-a-hash",
        "",
        "$argon2id$garbage",
        "$2b$12$short",
        PASSLIB_HASH[:-1],
        PASSLIB_HASH + "x",
        PASSLIB_HASH.replace("$2b$12$", "$2b$xx$"),
        PASSLIB_HASH.replace("$2b$12$", "$2b$03$"),
        PASSLIB_HASH.replace("$2b$12$", "$2b$99$"),
    ],
)
def test_malformed_hash_does_not_match(hashed):
    assert not verify_password("correct-password", hashed)


def test_dummy_verify_runs():
    dummy_verify_password()


async def login(session: AsyncSession, username: str, password: str) -> UserInDB:
    service = UserService(UserRepository(session), OutboxRepository(session), uow=None)
    return await service.authenticate(UserLoginRequest(username=username, password=password))


async def stored_hash(session: AsyncSession, user_id: int) -> str:
    return (await UserRepository(session).get_by_id(user_id)).hashed_password


@pytest.fixture
async def legacy_user(test_user: UserInDB, session: AsyncSession) -> UserInDB:
    await UserRepository(session).update_by_id(
        test_user.id, hashed_password=PASSLIB_HASH, is_active=True
    )
    return test_user


async def test_successful_login_upgrades_legacy_hash(legacy_user: UserInDB, session: AsyncSession):
    await login(session, legacy_user.username, "correct-password")

    upgraded = await stored_hash(session, legacy_user.id)
    assert upgraded.startswith("$argon2id$")
    assert await login(session, legacy_user.username, "correct-password")


async def test_failed_login_keeps_legacy_hash(legacy_user: UserInDB, session: AsyncSession):
    with pytest.raises(HTTPException):
        await login(session, legacy_user.username, "wrong-password")

    assert await stored_hash(session, legacy_user.id) == PASSLIB_HASH
