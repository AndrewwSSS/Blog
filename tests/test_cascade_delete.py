import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PostDB
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.schemas.comment import CommentCreate
from app.schemas.post import PostInDB
from app.schemas.user import UserInDB
from app.services import comment_service
from app.services.comment_service import CommentService
from tests.fixtures import (
    create_comment,
    session,
    test_post,
    test_user,
)


async def test_deleting_post_deletes_its_comments(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
):
    comment = await create_comment(test_user.id, test_post.id)

    deleted = await PostRepository(session).delete_by_id(test_post.id)

    assert deleted is True
    assert await CommentRepository(session).get_by_id(comment.id) is None


async def test_orm_delete_of_post_with_loaded_comments(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
):
    comment = await create_comment(test_user.id, test_post.id)
    post_db = await session.get(PostDB, test_post.id)
    await session.refresh(post_db, ["comments"])

    await session.delete(post_db)
    await session.commit()

    assert await CommentRepository(session).get_by_id(comment.id) is None


async def test_comment_on_missing_post_is_rejected(
    test_user: UserInDB,
    session: AsyncSession,
    monkeypatch,
):
    monkeypatch.setattr(comment_service, "validate_comment_content", None)
    service = CommentService(CommentRepository(session))

    with pytest.raises(HTTPException) as exc_info:
        await service.create(CommentCreate(content="hi", post_id=999), test_user)

    assert exc_info.value.status_code == 400
