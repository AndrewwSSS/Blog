from typing import Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.validation.base_content_validator import BaseContentValidator
from app.models import CommentDB
from app.schemas.comment import CommentRead, Comment
from app.schemas.user import UserRead


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_comments(self) -> [CommentRead]:
        query = select(CommentDB)
        cities_list = await self.session.execute(query)
        return [
            CommentRead.model_validate(comment[0])
            for comment in cities_list.fetchall()
        ]

    async def create_comment(
        self,
        comment: Comment,
        user: UserRead,
        content_validator_class: Type[BaseContentValidator]
    ) -> CommentRead:
        content_validator = content_validator_class()
        is_validated = await content_validator.validate_comment(
            comment.content
        )

        comment_db = CommentDB(
            **comment.dict(),
            owner_id=user.id,
            is_blocked=not is_validated
        )

        self.session.add(comment_db)
        await self.session.commit()
        await self.session.refresh(comment_db)
        return CommentRead.model_validate(
            comment_db
        )



