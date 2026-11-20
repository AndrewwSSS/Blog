from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth.utils import verify_token
from app.db.session import get_unit_of_work
from app.db.unit_of_work import UnitOfWork
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserInDB

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Access token from POST /api/v1/users/token",
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    uow: UnitOfWork = Depends(get_unit_of_work),
) -> UserInDB:
    if credentials is None:
        raise _unauthorized("Not authenticated")

    try:
        payload = verify_token(credentials.credentials)
    except jwt.InvalidTokenError as e:
        raise _unauthorized("Invalid authentication credentials") from e

    if payload.get("token_type") != "access":
        raise _unauthorized("Invalid token type")

    current_user = await UserRepository(uow.session).get_by_id(payload["user_id"])
    if not current_user:
        raise _unauthorized("Invalid authentication credentials")
    if not current_user.is_active:
        raise _unauthorized("Inactive user")

    return current_user


CurrentUserDependency = Annotated[UserInDB, Depends(get_current_user)]
