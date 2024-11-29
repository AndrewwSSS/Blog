from datetime import date

from sqlalchemy import update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer

from app.models import CommentDB
from app.schemas.comment import (
    CommentCreate,
    CommentInDB
)


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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

    async def create(
        self,
        comment: CommentCreate,
        user_id: int,
    ) -> CommentInDB:
        comment_db = CommentDB(
            **comment.model_dump(),
            owner_id=user_id,
        )

        self.session.add(comment_db)
        await self.session.commit()
        await self.session.refresh(comment_db)
        return CommentInDB.model_validate(
            comment_db
        )

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

    async def get_by_id(self, id: int) -> CommentInDB | None:
        query = select(CommentDB).where(CommentDB.id == id)
        result = await self.session.execute(query)
        comment_db = result.scalar_one_or_none()
        if comment_db:
            return CommentInDB.model_validate(
                comment_db
            )

    async def update_by_id(self, record_id: int, fields: dict) -> bool:
        query = (
            update(CommentDB)
            .where(CommentDB.id == record_id)
            .values(**fields)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(query)

        await self.session.commit()

        return result.rowcount > 0

    async def delete_by_id(self, record_id: int) -> bool:
        query = (
            delete(CommentDB)
            .where(CommentDB.id == record_id)
        )

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount > 0

    async def count_items(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(CommentDB)
        )

        return result.scalar()
