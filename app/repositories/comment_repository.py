from datetime import date

from sqlalchemy import select, func, Integer

from app.models import CommentDB
from app.repositories.AsyncDatabaseRepository import AsyncDatabaseRepository
from app.schemas.comment import (
    CommentInDB
)


class CommentRepository(AsyncDatabaseRepository):
    model = CommentDB
    pydantic_model = CommentInDB

    async def get_list(
        self,
        offset: int = None,
        limit: int = None,
        owner_id: int = None,
        post_id: int = None,
    ) -> [CommentInDB]:
        query = select(CommentDB)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        if owner_id:
            query = query.where(CommentDB.owner_id == owner_id)
        if post_id:
            query = query.where(CommentDB.post_id == post_id)

        result = await self.session.execute(query)
        comments = result.scalars().all()
        return [
            CommentInDB.model_validate(comment)
            for comment in comments
        ]

    async def get_analytics(
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

