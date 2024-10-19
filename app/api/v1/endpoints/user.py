from typing import List

from fastapi import APIRouter, Depends

from app.dependencies.services import get_user_service
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter()


@router.post("/register", response_model=UserRead)
async def create_user_endpoint(
    user: UserCreate,
    service: UserService = Depends(get_user_service)
):
    return await service.create_user(user)


@router.get("/", response_model=List[UserRead])
async def get_users_endpoint(
    service: UserService = Depends(get_user_service)
) -> [UserRead]:
    return await service.read_users()
