from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.schemas.comment import CommentFilterParams
from app.schemas.post import PostFilterParams, PostInDB
from app.schemas.user import UserInDB, UserUpdate
from app.services.comment_service import CommentService
from app.services.post_service import PostService
from tests.fixtures import (
    create_comment,
    create_post,
    create_user,
    session,
    test_post,
    test_user,
)


async def test_post_list_pages_with_filters(
    test_user: UserInDB,
    session: AsyncSession,
):
    other_user = await create_user()
    own_posts = [await create_post(test_user.id) for _ in range(5)]
    await create_post(other_user.id)
    await PostRepository(session).update_by_id(own_posts[0].id, is_blocked=True)
    service = PostService(PostRepository(session))

    page = await service.get_list(
        PostFilterParams(owner_id=test_user.id, page=2, limit=2)
    )

    assert page.total_pages == 2
    assert [post.id for post in page.items] == [own_posts[3].id, own_posts[4].id]


async def test_post_count_list_matches_filters(
    test_user: UserInDB,
    session: AsyncSession,
):
    other_user = await create_user()
    for _ in range(3):
        await create_post(test_user.id)
    await create_post(other_user.id)
    repository = PostRepository(session)

    assert await repository.count_list() == 4
    assert await repository.count_list(owner_id=test_user.id) == 3
    assert await repository.count_list(date_from=datetime.utcnow() + timedelta(days=1)) == 0


async def test_comment_list_pages_by_post(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
):
    other_post = await create_post(test_user.id)
    comments = [await create_comment(test_user.id, test_post.id) for _ in range(3)]
    await create_comment(test_user.id, other_post.id)
    service = CommentService(CommentRepository(session))

    page = await service.get_list(
        CommentFilterParams(post_id=test_post.id, page=2, limit=2)
    )

    assert page.total_pages == 2
    assert [comment.id for comment in page.items] == [comments[2].id]


async def test_comment_list_filters_by_date(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
):
    await create_comment(test_user.id, test_post.id)
    repository = CommentRepository(session)
    tomorrow = datetime.utcnow() + timedelta(days=1)

    assert await repository.get_list(date_from=tomorrow) == []
    assert len(await repository.get_list(date_to=tomorrow)) == 1
    assert await repository.count_list(date_from=tomorrow) == 0


@pytest.mark.parametrize("params_class", [PostFilterParams, CommentFilterParams])
@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"limit": 0},
        {"limit": 101},
        {"date_from": "2024-02-01", "date_to": "2024-01-01"},
    ],
)
def test_filter_params_reject_invalid_values(params_class, params):
    with pytest.raises(ValidationError):
        params_class(**params)


def test_user_update_accepts_turning_auto_reply_off():
    assert UserUpdate(post_auto_reply=False).post_auto_reply is False


@pytest.mark.parametrize("params", [{}, {"reply_after": 0.5}, {"reply_after": 0}])
def test_user_update_rejects_invalid_values(params):
    with pytest.raises(ValidationError):
        UserUpdate(**params)
