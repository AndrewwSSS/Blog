import asyncio

from celery import Celery

from app.core.config import settings
from app.db.session import get_session
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.user_repository import UserRepository
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


async def _create_reply_for_post(post_id: int) -> None:
    # get valid session
    session_gen = get_session()
    session = await anext(session_gen)

    # get post
    post_repo = PostRepository(session)
    post = await post_repo.get_post_by_id(post_id)
    if not post:
        raise ValueError("Post not found")

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
        settings.CONTENT_VALIDATOR_CLASS,
    )
    await session.close()
