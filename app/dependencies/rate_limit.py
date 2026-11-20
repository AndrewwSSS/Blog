from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status

from app.core.cache import hit_rate_limit


def per_ip_rate_limit(
    name: str, limit: int, window_seconds: int, *, fail_open: bool = False
) -> Callable[[Request], Awaitable[None]]:
    """Build a dependency that allows `limit` requests per client IP per window.

    The IP is `request.client.host`; behind a reverse proxy uvicorn sets it from
    X-Forwarded-For only for the addresses in FORWARDED_ALLOW_IPS.
    """

    async def check(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        retry_after = await hit_rate_limit(
            f"rate-limit:{name}:{client_ip}", limit, window_seconds, fail_open=fail_open
        )
        if retry_after:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, try again later",
                headers={"Retry-After": str(retry_after)},
            )

    return check
