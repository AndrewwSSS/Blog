from fastapi import Depends

from app.repositories.user_repository import UserRepository
from app.dependencies.repositories import get_user_repository
from app.services.user_service import UserService


def get_user_service(
    city_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(city_repository)
