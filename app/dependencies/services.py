from typing import Annotated

from fastapi import Depends

from app.dependencies.repositories import (
    UnitOfWorkDependency,
    get_comment_repository,
    get_outbox_repository,
    get_post_repository,
    get_user_repository,
)
from app.repositories.comment_repository import CommentRepository
from app.repositories.outbox_repository import OutboxRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.services.comment_service import CommentService
from app.services.post_service import PostService
from app.services.user_service import UserService


def get_user_service(
    uow: UnitOfWorkDependency,
    user_repository: UserRepository = Depends(get_user_repository),
    outbox_repository: OutboxRepository = Depends(get_outbox_repository),
) -> UserService:
    return UserService(user_repository, outbox_repository, uow)


def get_post_service(
    uow: UnitOfWorkDependency,
    post_repository: PostRepository = Depends(get_post_repository),
) -> PostService:
    return PostService(post_repository, uow)


def get_comment_service(
    uow: UnitOfWorkDependency,
    comment_repository: CommentRepository = Depends(get_comment_repository),
) -> CommentService:
    return CommentService(comment_repository, uow)


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]
PostServiceDependency = Annotated[PostService, Depends(get_post_service)]
CommentServiceDependency = Annotated[CommentService, Depends(get_comment_service)]
