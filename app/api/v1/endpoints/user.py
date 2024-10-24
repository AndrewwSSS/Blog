from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.dependencies.services import get_user_service
from app.schemas.jwt import LoginResponse
from app.schemas.jwt import TokenRefreshRequest
from app.schemas.user import User, UserRead
from app.schemas.user import UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=201)
async def create_user_endpoint(
    user: User,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(user)


@router.post("/token", response_model=LoginResponse)
async def login(
    user: User,
    service: UserService = Depends(get_user_service)
):
    return await service.get_jwt_tokens(user)


@router.post("/token/refresh")
async def refresh_access_token(
    token_request: TokenRefreshRequest,
    service: UserService = Depends(get_user_service)
):
    return await service.refresh_access_token(
        token_request.refresh_token
    )


@router.put("/me", response_model=UserRead)
async def update_user(
    user_update: UserUpdate,
    user: UserRead = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
) -> UserRead:
    return await service.update_user(user.id, user_update)


@router.get("/me", response_model=UserRead)
async def read_users_me(
    user: UserRead = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
) -> UserRead:
    return await service.get_user_by_id(
        user.id,
    )
