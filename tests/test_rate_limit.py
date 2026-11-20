from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import cache
from app.core.cache import hit_rate_limit
from app.core.config import settings
from app.main import app
from tests.conftest import FakeRedis

CLIENT_IP = "203.0.113.10"
OTHER_IP = "203.0.113.20"
LOGIN_URL = "/api/v1/users/token"
REGISTER_URL = "/api/v1/users/register"
RESEND_URL = "/api/v1/users/verification/resend"


def client_for(ip: str) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app, client=(ip, 4000)), base_url="http://test")


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with client_for(CLIENT_IP) as client:
        yield client


class DownRedis:
    def pipeline(self, transaction: bool = True):
        raise RedisConnectionError("redis down")

    async def set(self, *args, **kwargs):
        raise RedisConnectionError("redis down")


@pytest.fixture
def redis_down(monkeypatch) -> None:
    monkeypatch.setattr(cache, "redis", DownRedis())


async def login(client: AsyncClient) -> int:
    response = await client.post(LOGIN_URL, json={"username": "x", "password": "y"})
    return response.status_code


def registration(n: int) -> dict:
    return {"username": f"user{n}", "email": f"user{n}@example.com", "password": "password123"}


async def test_hits_within_limit_are_allowed_then_refused(fake_redis: FakeRedis):
    results = [await hit_rate_limit("k", 3, 60, fail_open=False) for _ in range(4)]

    assert results == [0, 0, 0, 60]
    assert fake_redis.expiry["k"] == 60


async def test_window_starts_at_the_first_hit(fake_redis: FakeRedis):
    await hit_rate_limit("k", 3, 60, fail_open=False)
    fake_redis.expiry["k"] = 42

    assert await hit_rate_limit("k", 3, 60, fail_open=False) == 0
    assert fake_redis.expiry["k"] == 42


@pytest.mark.parametrize("fail_open, expected", [(True, 0), (False, 60)])
async def test_redis_outage_follows_fail_open(redis_down, fail_open: bool, expected: int):
    assert await hit_rate_limit("k", 3, 60, fail_open=fail_open) == expected


async def test_login_is_limited_per_ip(client: AsyncClient):
    statuses = [await login(client) for _ in range(settings.RATE_LIMIT_LOGIN_PER_MINUTE)]
    response = await client.post(LOGIN_URL, json={"username": "x", "password": "y"})

    assert set(statuses) == {401}
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"
    async with client_for(OTHER_IP) as other_client:
        assert await login(other_client) == 401


async def test_register_is_limited_per_ip(client: AsyncClient):
    limit = settings.RATE_LIMIT_REGISTER_PER_HOUR
    statuses = [
        (await client.post(REGISTER_URL, json=registration(n))).status_code for n in range(limit)
    ]
    response = await client.post(REGISTER_URL, json=registration(limit))

    assert set(statuses) == {201}
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "3600"


async def test_resend_is_limited_per_ip_across_addresses(client: AsyncClient):
    limit = settings.RATE_LIMIT_RESEND_PER_HOUR
    statuses = [
        (await client.post(RESEND_URL, json={"email": f"a{n}@example.com"})).status_code
        for n in range(limit)
    ]
    response = await client.post(RESEND_URL, json={"email": "another@example.com"})

    assert set(statuses) == {202}
    assert response.status_code == 429


async def test_redis_outage_keeps_login_open_and_blocks_email_endpoints(
    client: AsyncClient, redis_down
):
    assert await login(client) == 401
    assert (await client.post(REGISTER_URL, json=registration(1))).status_code == 429
    assert (await client.post(RESEND_URL, json={"email": "a@example.com"})).status_code == 429
