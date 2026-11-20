import logging

from app.core.cache import invalidate_posts_cache
from app.core.validation import get_content_validator
from app.db.unit_of_work import UnitOfWork
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository

logger = logging.getLogger(__name__)


async def moderate_post(repository: PostRepository, uow: UnitOfWork, post_id: int) -> None:
    """Block or unblock a post according to the content validator.

    Raises ValueError when the post does not exist.
    """
    post = await repository.get_by_id(post_id)
    if not post:
        raise ValueError("Post not found")
    is_validated = await get_content_validator().validate_post(post.content, post.title)

    should_block = not is_validated
    if post.is_blocked != should_block:
        await repository.update_by_id(post_id, is_blocked=should_block)
        uow.after_commit(invalidate_posts_cache)
        logger.info(f"Post {post.id} is_blocked set to {should_block}")


async def moderate_comment(repository: CommentRepository, comment_id: int) -> None:
    """Block or unblock a comment according to the content validator.

    Raises ValueError when the comment does not exist.
    """
    comment = await repository.get_by_id(comment_id)
    if not comment:
        raise ValueError("Comment not found")
    is_validated = await get_content_validator().validate_comment(comment.content)

    should_block = not is_validated
    if comment.is_blocked != should_block:
        await repository.update_by_id(comment.id, is_blocked=should_block)
        logger.info(f"Comment {comment.id} is_blocked set to {should_block}")
