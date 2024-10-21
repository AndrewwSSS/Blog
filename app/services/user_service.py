from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.schemas.user import UserRead


class UserService:
    def __init__(self, user_repository: UserRepository):
        self.repository = user_repository

    async def create_user(self, user: UserCreate) -> UserRead:
        return await self.repository.create_user(user)

    async def read_users(self) -> [UserRead]:
        return await self.repository.get_users()