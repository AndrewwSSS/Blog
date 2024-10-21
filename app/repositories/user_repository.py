from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas.user import UserCreate
from app.schemas.user import UserRead


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(
        self,
        user: UserCreate,
    ) -> UserRead:
        user_db = User(
            username=user.username,
            hashed_password=user.password,
            email=user.email,
        )
        self.session.add(user_db)
        await self.session.commit()
        await self.session.refresh(user_db)

        return UserRead.model_validate(
            user_db
        )

    async def get_users(self) -> [UserRead]:
        query = select(User)
        cities_list = await self.session.execute(query)
        return [
            UserRead.model_validate(city[0])
            for city in cities_list.fetchall()
        ]

    async def get_user_by_id(self, user_id: int) -> UserRead:
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user_db = result.scalar_one_or_none()
        if user_db:
            return UserRead.model_validate(
                user_db
            )

