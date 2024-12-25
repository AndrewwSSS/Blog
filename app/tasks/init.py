import asyncio

from celery import Celery

from app.core.config import settings
from app.db.session import async_session
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.schemas.comment import Comment

celery = Celery(
    "tasks",
    broker=settings.celery_broker_url,
)


@celery.task
def create_reply_for_post(post_id: int):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(_create_reply_for_post(post_id))
    else:
        loop.run_until_complete(_create_reply_for_post(post_id))


@celery.task
def validate_post_content(
    post_id: int
):
    run_coroutine(
        run_post_validation(
            post_id,
        )
    )


@celery.task
def validate_comment_content(
    comment_id: int
):
    run_coroutine(run_comment_validation(
        comment_id,
    ))


def run_coroutine(coroutine):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.ensure_future(coroutine)
    else:
        loop.run_until_complete(coroutine)


async def run_post_validation(post_id: int):
    from app.services.post_service import PostService

    async with async_session() as session:
        post_repo = PostRepository(session)
        post_service = PostService(post_repo)
        await post_service.validate_post_content(
            post_id
        )


async def run_comment_validation(comment_id: int):
    from app.services.comment_service import CommentService

    async with async_session() as session:
        comment_repo = CommentRepository(session)
        comment_service = CommentService(comment_repo)
        await comment_service.validate_comment_content(
            comment_id
        )


async def _create_reply_for_post(post_id: int) -> None:
    async with async_session() as session:
        post_repo = PostRepository(session)
        post = await post_repo.get_post_by_id(post_id)
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
        comment = Comment(
            content=reply_content,
            post_id=post_id,
        )
        await comment_repo.create_comment(
            comment,
            post.owner_id,
        )
