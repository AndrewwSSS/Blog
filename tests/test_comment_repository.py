from datetime import timedelta

import pytest

from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import Comment
from app.schemas.user import UserRead
from tests.conftest import MockContentValidator
from tests.conftest import async_session_maker
from datetime import date

from tests.conftest import create_comment


@pytest.mark.asyncio
async def test_create_comment(test_post: UserRead, test_user: UserRead):
    async with async_session_maker() as session:
        repository = CommentRepository(session)
        comment = Comment(content="Test comment", post_id=test_post.id)

        created_comment = await repository.create_comment(
            comment,
            test_user.id,
        )

    assert created_comment.content == comment.content
    assert created_comment.owner_id == test_user.id
    assert created_comment.is_blocked is False


async def test_get_comments(test_comments):
    async with async_session_maker() as session:
        comment_repo = CommentRepository(session)
        comments = await comment_repo.get_comments()

    assert isinstance(comments, list)
    assert len(comments) == len(test_comments)

    for ind, comment in enumerate(test_comments):
        assert comments[ind] == comment


async def test_get_comments_analytics(test_post):
    comment_1 = await create_comment(
        test_post.id,
        test_post.owner_id
    )
    comment_2 = await create_comment(
        test_post.id,
        test_post.owner_id
    )
    comment_3 = await create_comment(
        test_post.id,
        test_post.owner_id
    )
    comment_4 = await create_comment(
        test_post.id,
        test_post.owner_id
    )

    async with async_session_maker() as session:
        repository = CommentRepository(session)
        analytics = await repository.get_comments_analytics(
            date_from=date.today() - timedelta(days=1),
            date_to=date.today(),
        )

    assert len(analytics) == 1
    record = analytics[0]
    assert record[0] == date.today()
    assert record[1] == 4
    assert record[2] == 0
