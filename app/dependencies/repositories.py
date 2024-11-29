from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.db.session import get_session


def get_user_repository(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)


def get_post_repository(session: AsyncSession = Depends(get_session)) -> PostRepository:
    return PostRepository(session)


def get_comment_repository(session: AsyncSession = Depends(get_session)) -> CommentRepository:
    return CommentRepository(session)


UserRepoDependency = Annotated[UserRepository, Depends(get_user_repository)]
PostRepoDependency = Annotated[PostRepository, Depends(get_post_repository)]
CommentRepoDependency = Annotated[CommentRepository, Depends(get_comment_repository)]
