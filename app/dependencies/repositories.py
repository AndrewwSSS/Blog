from typing import Annotated

from fastapi import Depends

from app.db.session import get_unit_of_work
from app.db.unit_of_work import UnitOfWork
from app.repositories.comment_repository import CommentRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository

UnitOfWorkDependency = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_user_repository(uow: UnitOfWorkDependency) -> UserRepository:
    return UserRepository(uow.session)


def get_post_repository(uow: UnitOfWorkDependency) -> PostRepository:
    return PostRepository(uow.session)


def get_comment_repository(uow: UnitOfWorkDependency) -> CommentRepository:
    return CommentRepository(uow.session)


def get_outbox_repository(uow: UnitOfWorkDependency) -> OutboxRepository:
    return OutboxRepository(uow.session)


UserRepoDependency = Annotated[UserRepository, Depends(get_user_repository)]
PostRepoDependency = Annotated[PostRepository, Depends(get_post_repository)]
CommentRepoDependency = Annotated[CommentRepository, Depends(get_comment_repository)]
