from datetime import date, datetime

from sqlalchemy import Integer, Select, func, select

from app.models import CommentDB
from app.repositories.AsyncDatabaseRepository import AsyncDatabaseRepository
from app.schemas.comment import CommentInDB


class CommentRepository(AsyncDatabaseRepository):
    model = CommentDB
    pydantic_model = CommentInDB

    @staticmethod
    def _apply_filters(
        query: Select,
        owner_id: int = None,
        post_id: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> Select:
        query = query.where(CommentDB.is_blocked.is_(False))
        if owner_id:
            query = query.where(CommentDB.owner_id == owner_id)
        if post_id:
            query = query.where(CommentDB.post_id == post_id)
        if date_from:
            query = query.where(CommentDB.date_posted >= date_from)
        if date_to:
            query = query.where(CommentDB.date_posted <= date_to)
        return query

    async def get_list(
        self,
        offset: int = None,
        limit: int = None,
        owner_id: int = None,
        post_id: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> list[CommentInDB]:
        query = self._apply_filters(
            select(CommentDB), owner_id, post_id, date_from, date_to
        ).order_by(CommentDB.id)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        comments = result.scalars().all()
        return [CommentInDB.model_validate(comment) for comment in comments]

    async def count_list(
        self,
        owner_id: int = None,
        post_id: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> int:
        query = self._apply_filters(
            select(func.count()).select_from(CommentDB),
            owner_id,
            post_id,
            date_from,
            date_to,
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_analytics(self, date_from: date, date_to: date):
        query = (
            select(
                func.date(CommentDB.date_posted).label("date"),
                func.count(CommentDB.id).label("total_comments"),
                func.sum(func.cast(CommentDB.is_blocked, Integer)).label("blocked_comments"),
            )
            .where(func.date(CommentDB.date_posted) >= date_from)
            .where(func.date(CommentDB.date_posted) <= date_to)
            .group_by(func.date(CommentDB.date_posted))
            .order_by(func.date(CommentDB.date_posted))
        )

        result = await self.session.execute(query)
        return result.all()
