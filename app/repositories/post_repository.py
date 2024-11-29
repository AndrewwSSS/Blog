from datetime import datetime
from typing import Iterable

from sqlalchemy import (
    update,
    select,
    delete, func
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PostDB
from app.core.async_elasticsearch_client import AsyncElasticsearchClient
from app.schemas.post import Post, PostInDB


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_list(
        self,
        offset: int = None,
        limit: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
        owner_id: int = None,
    ) -> [PostInDB]:
        query = select(PostDB)

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        if date_from:
            query = query.where(
                PostDB.date_posted >= date_from
            )
        if date_to:
            query = query.where(
                PostDB.date_posted <= date_to
            )
        if owner_id:
            query = query.where(
                PostDB.owner_id == owner_id
            )

        result = await self.session.execute(query)
        posts = result.scalars().all()

        return [
            PostInDB.model_validate(post)
            for post in posts
        ]

    async def create(
        self,
        post: Post,
        user_id: int,
    ) -> PostInDB:
        post_db = PostDB(
            **post.model_dump(),
            owner_id=user_id,
        )

        self.session.add(post_db)
        await self.session.commit()
        await self.session.refresh(post_db)

        return PostInDB.model_validate(
            post_db
        )

    async def get_by_id(self, post_id: int) -> PostInDB | None:
        query = select(PostDB).where(PostDB.id == post_id)
        result = await self.session.execute(query)
        post_db = result.scalar_one_or_none()
        if post_db:
            return PostInDB.model_validate(post_db)

    async def get_by_ids(self, records_ids: Iterable[int]) -> list[PostInDB]:
        query = select(PostDB).where(PostDB.id.in_(records_ids))
        result = await self.session.execute(query)
        posts_list = result.scalars().all()
        return [
            PostInDB.model_validate(post)
            for post in posts_list
        ]

    async def update_by_id(self, record_id: int, fields: dict) -> bool:
        query = (
            update(PostDB)
            .where(PostDB.id == record_id)
            .values(**fields)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount == 1

    async def delete_by_id(self, post_id: int) -> bool:
        query = (
            delete(PostDB)
            .where(PostDB.id == post_id)
        )

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount == 1

    async def search(self, query_string: str) -> list[PostInDB]:
        es_repo = AsyncElasticsearchClient()
        search_results = await es_repo.search_by_template(
            index_name="posts",
            search_template_id="full-text-search",
            params={
                "query_string": query_string,
            },
        )

        ordered_ids = [
            int(item["_id"])
            for item in search_results["hits"]["hits"]
        ]

        posts = await self.get_by_ids(
           ordered_ids
        )

        id_to_post = {post.id: post for post in posts}

        return [
            PostInDB.model_validate(id_to_post[post_id])
            for post_id in ordered_ids
            if post_id in id_to_post
        ]

    async def count_items(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(PostDB)
        )

        return result.scalar()
