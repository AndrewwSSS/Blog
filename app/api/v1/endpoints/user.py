from fastapi import APIRouter

from app.core.auth.dependencies import CurrentUserDependency
from app.dependencies.services import UserServiceDependency
from app.schemas.jwt import (
    LoginResponse,
    TokenRefreshResponse,
    TokenRefreshRequest
)
from app.schemas.user import (
    UserRegister,
    UserRead,
    UserLoginRequest,
    UserUpdate
)

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
async def create_user_endpoint(
    user: UserRegister,
    service: UserServiceDependency,
):
    return await service.create_user(user)


@router.post("/token", response_model=LoginResponse)
async def login(
    user: UserLoginRequest,
    service: UserServiceDependency,
):
    return await service.login_user(user)


@router.post("/token/refresh", response_model=TokenRefreshResponse)
async def refresh_access_token(
    token_request: TokenRefreshRequest,
    service: UserServiceDependency
):
    return await service.refresh_access_token(
        token_request.refresh_token
    )


@router.put("/me", response_model=UserRead)
async def update_user(
    user_update: UserUpdate,
    current_user: CurrentUserDependency,
    service: UserServiceDependency
):
    return await service.update_by_id(current_user.id, user_update)


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: CurrentUserDependency,
    service: UserServiceDependency
):
    return await service.get_user_by_id(current_user.id)


@router.get("/verification/{token}")
async def verify_user(
    token: str,
    service: UserServiceDependency
):
    return await service.verify_user(
        token
    )
