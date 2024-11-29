from datetime import timedelta
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import CommentDB
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate,CommentInDB
from app.schemas.post import PostInDB
from app.schemas.user import UserRead
from tests.fixtures import (
    create_comment,
    test_comment,
    test_user,
    session,
    test_comments,
    test_post
)


@pytest.mark.asyncio
async def test_create_comment(
    test_post: UserRead,
    test_user: UserRead,
    session
):
    comment_content = "Test comment"
    repository = CommentRepository(session)
    new_comment = CommentCreate(content=comment_content, post_id=test_post.id)
    created_comment = await repository.create(
        new_comment,
        test_user.id,
    )

    assert created_comment.content == comment_content
    assert created_comment.owner_id == test_user.id
    assert created_comment.is_blocked is False

    query = select(CommentDB).where(CommentDB.content == comment_content)
    result = await session.execute(query)
    retrieved_comment = result.scalar_one_or_none()

    assert retrieved_comment is not None
    assert retrieved_comment.content == created_comment.content
    assert retrieved_comment.owner_id == created_comment.owner_id
    assert retrieved_comment.post_id == created_comment.post_id


async def test_get_list_without_args(
    test_comments: [CommentDB],
    session: AsyncSession,
):
    comment_repo = CommentRepository(session)
    result_comments = await comment_repo.get_list()

    assert isinstance(result_comments, list)
    assert len(result_comments) == len(test_comments)

    for ind, comment in enumerate(test_comments):
        assert result_comments[ind] == comment


async def test_get_list_with_offset(
    test_comments: [CommentDB],
    session: AsyncSession,
):
    comment_repo = CommentRepository(session)
    result_comments = await comment_repo.get_list(
        offset=1,
    )

    assert isinstance(result_comments, list)
    assert len(test_comments) - len(result_comments) == 1

    for ind, comment in enumerate(test_comments[1::]):
        assert comment in result_comments


async def test_get_list_with_limit_and_offset(
    test_comments: [CommentDB],
    session: AsyncSession,
):
    comment_repo = CommentRepository(session)
    result_comments = await comment_repo.get_list(
        limit=2,
        offset=1,
    )

    assert isinstance(result_comments, list)
    assert len(result_comments) == 2

    for ind, comment in enumerate(result_comments):
        assert comment == test_comments[ind + 1]


async def test_get_list_with_limit(test_comments, session):
    comment_repo = CommentRepository(session)
    result_comments = await comment_repo.get_list(
        limit=3,
    )
    assert isinstance(result_comments, list)
    assert len(result_comments) == 3

    for ind, comment in enumerate(result_comments):
        assert comment == test_comments[ind]


async def test_get_comments_analytics(
    test_post: PostInDB,
    session: AsyncSession,
):
    await create_comment(
        test_post.id,
        test_post.owner_id
    )
    await create_comment(
        test_post.id,
        test_post.owner_id
    )
    await create_comment(
        test_post.id,
        test_post.owner_id
    )
    await create_comment(
        test_post.id,
        test_post.owner_id
    )
    today = date.today()

    repository = CommentRepository(session)
    analytics = await repository.get_analytics(
        date_from=today - timedelta(days=1),
        date_to=today,
    )

    assert len(analytics) == 1
    record = analytics[0]

    assert record[0] == today.strftime("%Y-%m-%d")
    assert record[1] == 4  # message count
    assert record[2] == 0  # blocked messages count


async def test_by_id(
    test_comment: CommentInDB,
    session: AsyncSession,
):
    comment_repo = CommentRepository(session)
    result_comment = await comment_repo.get_by_id(test_comment.id)

    assert result_comment == test_comment


async def test_update_by_id(
    test_comment: CommentInDB,
    session: AsyncSession,
):
    new_content_value = "test content"
    new_is_blocked_value = True
    comment_repo = CommentRepository(session)
    updated = await comment_repo.update_by_id(
        record_id=test_comment.id,
        fields={
            "content": new_content_value,
            "is_blocked": new_is_blocked_value
        }
    )
    result_comment = await comment_repo.get_by_id(
        test_comment.id
    )

    assert updated
    assert result_comment.content == new_content_value
    assert result_comment.owner_id == test_comment.owner_id
    assert result_comment.is_blocked is True
    assert result_comment.post_id == test_comment.post_id


async def test_delete_by_id(
    test_comment: CommentInDB,
    session: AsyncSession,
):
    comment_repo = CommentRepository(session)
    deleted = await comment_repo.delete_by_id(
        test_comment.id
    )
    deleted_comment = await comment_repo.get_by_id(
        test_comment.id
    )

    assert deleted
    assert deleted_comment is None
