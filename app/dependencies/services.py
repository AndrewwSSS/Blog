from fastapi import Depends

from app.dependencies.repositories import get_comment_repository
from app.dependencies.repositories import get_post_repository
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
from app.dependencies.repositories import get_user_repository
from app.services.comment_service import CommentService
from app.services.post_service import PostService
from app.services.user_service import UserService


def get_user_service(
    city_repository: UserRepository = Depends(get_user_repository)
) -> UserService:
    return UserService(city_repository)


def get_post_service(
    post_repository: PostRepository = Depends(get_post_repository)
) -> PostService:
    return PostService(post_repository)


def get_comment_service(
    comment_repository: CommentRepository = Depends(get_comment_repository)
) -> CommentService:
    return CommentService(comment_repository)
