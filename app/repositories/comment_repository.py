from typing import Type
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.core.validation.base_content_validator import BaseContentValidator
from app.models import CommentDB
from app.schemas.comment import CommentRead, Comment


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
        user_id: int,
        content_validator_class: Type[BaseContentValidator]
    ) -> CommentRead:
        content_validator = content_validator_class()
        is_validated = await content_validator.validate_comment(
            comment.content
        )

        comment_db = CommentDB(
            **comment.model_dump(),
            owner_id=user_id,
            is_blocked=not is_validated
        )

        self.session.add(comment_db)
        await self.session.commit()
        await self.session.refresh(comment_db)
        return CommentRead.model_validate(
            comment_db
        )

    async def get_comments_analytics(
        self,
        date_from: date,
        date_to: date
    ):
        query = (
            select(
                func.date(CommentDB.date_posted).label("date"),
                func.count(CommentDB.id).label("total_comments"),
                func.sum(func.cast(CommentDB.is_blocked, Integer)).label("blocked_comments")
            )
            .where(func.date(CommentDB.date_posted) >= date_from)
            .where(func.date(CommentDB.date_posted) <= date_to)
            .group_by(func.date(CommentDB.date_posted))
            .order_by(func.date(CommentDB.date_posted))
        )

        result = await self.session.execute(query)
        return result.all()
