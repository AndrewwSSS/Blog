from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.post_repository import PostRepository
from app.schemas.post import Post, PostInDB
from app.schemas.user import UserInDB
from tests.fixtures import (
    test_user,
    session,
    test_posts,
    test_post
)


async def test_create_post(
    test_user: UserInDB,
    session: AsyncSession,
):
    repository = PostRepository(session)
    post = Post(content="Test content", title="Test title")

    created_post = await repository.create(
        **post.model_dump(),
        owner_id=test_user.id,
    )

    assert created_post.content == post.content
    assert created_post.title == post.title
    assert created_post.owner_id == test_user.id
    assert created_post.is_blocked is False


async def test_get_list_without_params(
    test_posts: [PostInDB],
    session: AsyncSession,
):
    repository = PostRepository(session)
    posts = await repository.get_list()

    assert isinstance(posts, list)
    assert len(posts) == len(test_posts)

    for ind, post in enumerate(posts):
        assert post in test_posts


async def test_get_list_with_offset(
    test_posts: [PostInDB],
    session: AsyncSession
):
    repository = PostRepository(
        session
    )
    posts_result = await repository.get_list(
        offset=2
    )

    for ind, post in enumerate(posts_result):
        assert post == test_posts[ind + 2]


async def test_get_list_with_limit(
    test_posts: [PostInDB],
    session: AsyncSession
):
    repository = PostRepository(
        session
    )
    posts_result = await repository.get_list(
        limit=1
    )

    assert len(posts_result) == 1
    assert posts_result[0] == test_posts[0]


async def test_get_list_with_offset_and_limit(
    test_posts: [PostInDB],
    session: AsyncSession
):
    repository = PostRepository(
        session
    )
    posts_result = await repository.get_list(
        offset=1,
        limit=2
    )

    assert len(posts_result) == 2

    for ind, post in enumerate(posts_result):
        assert post == test_posts[ind + 1]


async def test_get_by_id(
    test_post: PostInDB,
    session: AsyncSession,
):
    repository = PostRepository(session)
    post = await repository.get_by_id(test_post.id)

    assert post is not None
    assert post.id == test_post.id
    assert post.title == test_post.title
    assert post.owner_id == test_post.owner_id
    assert post.is_blocked == test_post.is_blocked
    assert post.content == test_post.content


async def test_get_by_ids(
    test_posts: [PostInDB],
    session: AsyncSession
):
    posts_ids = [post.id for post in test_posts]
    repository = PostRepository(session)
    result_posts = await repository.get_by_ids(
        records_ids=posts_ids
    )

    for post in result_posts:
        assert post in test_posts


async def test_update_by_id(
    test_post: PostInDB,
    session: AsyncSession,
):
    new_content_value = "test content change"
    new_title_value = "test title change"

    repository = PostRepository(session)
    updated = await repository.update_by_id(
        record_id=test_post.id,
        content=new_content_value,
        title=new_title_value
    )

    updated_post = await repository.get_by_id(test_post.id)

    assert updated is True
    assert updated_post is not None
    assert updated_post.content == new_content_value
    assert updated_post.title == new_title_value

    not_updated_fields = updated_post.model_dump(
        exclude={"content", "title"}
    )

    for field, value in not_updated_fields.items():
        assert getattr(test_post, field) == value


async def test_delete_by_id(
    test_post: PostInDB,
    session: AsyncSession
):
    repository = PostRepository(session)
    deleted = await repository.delete_by_id(
        test_post.id,
    )
    deleted_post = await repository.get_by_id(test_post.id)

    assert deleted
    assert deleted_post is None
