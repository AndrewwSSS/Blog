from typing import List

from fastapi import APIRouter, Depends

from app.core.auth.dependencies import get_current_user
from app.dependencies.services import get_user_service
from app.schemas.jwt import TokenRefreshRequest
from app.schemas.user import User, UserRead
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def create_user_endpoint(
    user: User,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(user)


@router.get("/", response_model=List[UserRead])
async def get_users_endpoint(
    user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
) -> [UserRead]:
    return await service.read_users()


@router.post("/token")
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
