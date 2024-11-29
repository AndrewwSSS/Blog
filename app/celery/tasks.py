import asyncio
import logging

from celery import Celery

from app.core.config import settings
from app.db.session import async_session
from app.core.async_elasticsearch_client import AsyncElasticsearchClient
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.schemas.comment import CommentCreate


celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
)
celery.conf["task_always_eager"] = False

logger = logging.getLogger(__file__)


def run_coroutine(coroutine):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(coroutine)
    else:
        loop.run_until_complete(coroutine)


@celery.task
def create_reply_for_post(post_id: int):
    run_coroutine(_create_reply_for_post(post_id))


@celery.task
def validate_post_content(post_id: int):
    run_coroutine(run_post_validation(post_id))


@celery.task
def validate_comment_content(comment_id: int):
    run_coroutine(run_comment_validation(comment_id))


@celery.task
def update_post_document(post_id: int):
    run_coroutine(run_update_post_document(post_id))


@celery.task
def add_post_to_elastic_search(post_id: int):
    run_coroutine(run_adding_post_to_elastic_search(post_id))


@celery.task
def delete_post_document(post_id: int):
    run_coroutine(run_delete_post_document(post_id))


async def run_delete_post_document(post_id: int):
    es_repo = AsyncElasticsearchClient()
    await es_repo.delete_document(
        index_name="posts",
        document_id=post_id,
    )


async def run_update_post_document(post_id: int):
    from app.services.post_service import PostRepository
    async with async_session() as session:
        post_repo = PostRepository(session)
        post = await post_repo.get_by_id(
            post_id
        )
        if not post:
            logger.error(
                "Post with if {post_id} no found"
            )
            return
        es_repo = AsyncElasticsearchClient()
        response = await es_repo.update_document(
            index_name="posts",
            document_id=post_id,
            updated_document={
                "doc": post.dict(exclude_none=True)
            }
        )
        logger.info(f"Update response: {response}")


async def run_post_validation(post_id: int):
    from app.services.post_service import PostService

    async with async_session() as session:
        post_repo = PostRepository(session)
        post_service = PostService(post_repo)
        await post_service.validate_content(
            post_id
        )


async def run_comment_validation(comment_id: int):
    from app.services.comment_service import CommentService

    async with async_session() as session:
        comment_repo = CommentRepository(session)
        comment_service = CommentService(comment_repo)
        await comment_service.validate_content(
            comment_id
        )


async def run_adding_post_to_elastic_search(post_id: int):
    from app.services.post_service import PostRepository
    async with async_session() as session:
        post_repo = PostRepository(session)
        post = await post_repo.get_by_id(
            post_id
        )
        if not post:
            logger.error(
                "Post not found in database"
            )
            return
        es_repo = AsyncElasticsearchClient()

        await es_repo.create_document(
            index_name="posts",
            document_id=post.id,
            document={
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "date_posted": post.date_posted,
            }
        )


async def _create_reply_for_post(post_id: int) -> None:
    async with async_session() as session:
        post_repo = PostRepository(session)
        post = await post_repo.get_by_id(post_id)
        if not post:
            raise ValueError("Post not found")
        if post.is_blocked:
            print("Post blocked, reply generating has been canceled")
            return
        reply_generator = settings.REPLY_GENERATOR_CLASS()
        reply_content = await reply_generator.generate_post_reply(
            post.title, post.content,
        )

        comment_repo = CommentRepository(session)
        comment = CommentCreate(
            content=reply_content,
            post_id=post_id,
        )
        await comment_repo.create(
            comment,
            post.owner_id,
        )
