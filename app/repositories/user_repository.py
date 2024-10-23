from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models import UserDB
from app.schemas.user import User
from app.schemas.user import UserInDB
from app.schemas.user import UserRead
from app.schemas.user import UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(
        self,
        user: User,
    ) -> UserRead:

        user_db = UserDB(
            username=user.username,
            hashed_password=get_password_hash(user.password),
            email=user.email,
        )
        self.session.add(user_db)
        await self.session.commit()
        await self.session.refresh(user_db)

        return UserRead.model_validate(
            user_db
        )

    async def get_users(self) -> [UserRead]:
        query = select(UserDB)
        users_list = await self.session.execute(query)
        return [
            UserRead.model_validate(city[0])
            for city in users_list.fetchall()
        ]

    async def get_user_by_id(self, user_id: int) -> UserRead | None:
        user_db = await self._get_user_by_id(user_id)
        if user_db:
            return UserRead.model_validate(
                user_db
            )

    async def _get_user_by_id(self, user_id: int) -> UserDB:
        query = select(UserDB).where(UserDB.id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> UserInDB | None:
        query = select(UserDB).where(UserDB.username == username)
        result = await self.session.execute(query)
        user_db = result.scalar_one_or_none()
        if user_db:
            return UserInDB.model_validate(
                user_db
            )

    async def update_user_by_id(
        self,
        user_id: int,
        user: UserUpdate,
    ) -> UserRead | None:
        user_db = await self._get_user_by_id(
            user_id=user_id,
        )

        if user.post_auto_reply:
            user_db.post_auto_reply = user.post_auto_reply
        if user.reply_after:
            user_db.reply_after = user.reply_after

        print(user_db)
        await self.session.commit()
        await self.session.refresh(user_db)
        return UserRead.model_validate(user_db)

    async def get_user_hashed_password(self, user_id: int) -> str | None:
        query = select(UserDB).where(UserDB.id == user_id)
        result = await self.session.execute(query)
        user_db = result.scalar_one_or_none()
        if user_db:
            return user_db.hashed_password
