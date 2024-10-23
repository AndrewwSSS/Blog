from app.repositories.post_repository import PostRepository
from app.schemas.post import Post
from tests.conftest import MockContentValidator
from tests.conftest import async_session_maker


async def test_create_post(test_user):
    async with async_session_maker() as session:
        repository = PostRepository(session)
        post = Post(content="Test content", title="Test title")

        created_post = await repository.create_post(
            post,
            test_user.id,
        )

    assert created_post.content == post.content
    assert created_post.title == post.title
    assert created_post.owner_id == test_user.id
    assert created_post.is_blocked is False


async def test_get_posts(test_posts):
    async with async_session_maker() as session:
        repository = PostRepository(session)
        posts = await repository.get_posts()

    assert isinstance(posts, list)
    assert len(posts) == len(test_posts)

    for ind, post in enumerate(posts):
        assert post in test_posts


async def test_get_post_by_id(test_post):
    async with async_session_maker() as session:
        repository = PostRepository(session)
        post = await repository.get_post_by_id(test_post.id)

    assert post is not None
    assert post.id == test_post.id
    assert post.title == test_post.title
    assert post.owner_id == test_post.owner_id
    assert post.is_blocked == test_post.is_blocked
    assert post.content == test_post.content



