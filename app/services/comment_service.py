from datetime import date

from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import Comment
from app.schemas.comment import CommentRead
from app.schemas.user import UserRead
from app.tasks.init import validate_comment_content


class CommentService:
    def __init__(self, comment_repository: CommentRepository) -> None:
        self.repository = comment_repository

    async def get_comments(self) -> [CommentRead]:
        return await self.repository.get_comments()

    async def create_comment(self, comment: Comment, user: UserRead) -> CommentRead:
        comment_created = await self.repository.create_comment(
            comment,
            user.id,
        )
        validate_comment_content.delay(comment_created.id)
        return comment_created

    async def get_comments_analytics(self, date_from: date, date_to: date) -> dict:
        return await self.repository.get_comments_analytics(date_from, date_to)
