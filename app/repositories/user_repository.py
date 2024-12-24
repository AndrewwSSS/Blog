from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models import UserDB
from app.repositories.AsyncDatabaseRepository import AsyncDatabaseRepository
from app.schemas.user import UserRegister
from app.schemas.user import UserInDB


class UserRepository(AsyncDatabaseRepository):
    model = UserDB
    pydantic_model = UserInDB

    async def get_list(
        self,
        offset: int = None,
        limit: int = None
    ) -> [UserInDB]:
        query = select(UserDB)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        users_list = result.scalars().all()
        return [
            UserInDB.model_validate(user)
            for user in users_list
        ]

    async def get_by_username(self, username: str) -> UserInDB | None:
        query = select(UserDB).where(UserDB.username == username)
        result = await self.session.execute(query)
        user_db = result.scalar_one_or_none()
        if user_db:
            return UserInDB.model_validate(
                user_db
            )


    async def update_by_email(
        self,
        email: str,
        fields: dict,
    ) -> bool:
        query = (
            update(UserDB)
            .where(UserDB.email == email)
            .values(**fields)
        )

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount == 1

    async def get_by_email(self, email: str) -> UserInDB | None:
        query = select(UserDB).where(UserDB.email == email)
        result = await self.session.execute(query)
        user_db = result.scalar_one_or_none()
        if user_db:
            return UserInDB.model_validate(
                user_db
            )
