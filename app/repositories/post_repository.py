import logging
from datetime import datetime

from sqlalchemy import (
    select,
)

from app.models import PostDB
from app.core.async_elasticsearch_client import AsyncElasticsearchClient
from app.repositories.AsyncDatabaseRepository import AsyncDatabaseRepository
from app.schemas.post import PostInDB

logger = logging.getLogger(__name__)


class PostRepository(AsyncDatabaseRepository):
    model = PostDB
    pydantic_model = PostInDB

    async def get_list(
        self,
        offset: int = None,
        limit: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
        owner_id: int = None,
    ) -> list[PostInDB]:
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

    async def search(self, query_string: str) -> list[PostInDB]:
        es_repo = AsyncElasticsearchClient()
        search_results = await es_repo.search_by_template(
            index_name="posts",
            search_template_id="full-text-search",
            params={
                "query_string": query_string,
            },
        )

        logger.debug(f"Search results: {search_results}")

        ordered_ids = [
            int(item["_id"])
            for item in search_results["hits"]["hits"]
        ]

        if not ordered_ids:
            return []

        posts = await self.get_by_ids(
           ordered_ids
        )

        id_to_post = {post.id: post for post in posts}

        return [
            PostInDB.model_validate(id_to_post[post_id])
            for post_id in ordered_ids
            if post_id in id_to_post
        ]
