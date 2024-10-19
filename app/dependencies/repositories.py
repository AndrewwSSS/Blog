from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.repositories.user_repository import UserRepository
from app.db.session import get_session


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)
