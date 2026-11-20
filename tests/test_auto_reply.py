import pytest

from app.celery import tasks
from app.db.unit_of_work import UnitOfWork
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.schemas.post import PostInDB
from tests.fixtures import async_session_maker


class CountingReplyGenerator:
    calls = 0

    async def generate_post_reply(self, title: str, content: str) -> str:
        CountingReplyGenerator.calls += 1
        return "auto reply"


@pytest.fixture(autouse=True)
def reply_generator(monkeypatch) -> type[CountingReplyGenerator]:
    CountingReplyGenerator.calls = 0
    monkeypatch.setattr(tasks, "async_session", async_session_maker)
    monkeypatch.setattr(tasks, "get_reply_generator", CountingReplyGenerator)
    return CountingReplyGenerator


async def comments_on(post_id: int) -> list[str]:
    async with async_session_maker() as session:
        return [c.content for c in await CommentRepository(session).get_list(post_id=post_id)]


async def auto_replied_at(post_id: int):
    async with async_session_maker() as session:
        return (await PostRepository(session).get_by_id(post_id)).auto_replied_at


async def test_second_run_skips_the_ai_call_and_the_comment(test_post: PostInDB, reply_generator):
    await tasks._create_reply_for_post(test_post.id)
    await tasks._create_reply_for_post(test_post.id)

    assert await comments_on(test_post.id) == ["auto reply"]
    assert reply_generator.calls == 1
    assert await auto_replied_at(test_post.id) is not None


async def test_overlapping_run_that_loses_the_claim_adds_no_comment(
    test_post: PostInDB, monkeypatch
):
    class OtherRunFinishesFirst:
        async def generate_post_reply(self, title: str, content: str) -> str:
            async with UnitOfWork(async_session_maker) as other:
                assert await PostRepository(other.session).claim_auto_reply(test_post.id)
            return "late reply"

    monkeypatch.setattr(tasks, "get_reply_generator", OtherRunFinishesFirst)

    await tasks._create_reply_for_post(test_post.id)

    assert await comments_on(test_post.id) == []


async def test_failed_comment_insert_releases_the_claim(test_post: PostInDB, monkeypatch):
    async def failing_create(self, **data):
        raise RuntimeError("insert failed")

    monkeypatch.setattr(CommentRepository, "create", failing_create)

    with pytest.raises(RuntimeError):
        await tasks._create_reply_for_post(test_post.id)

    assert await auto_replied_at(test_post.id) is None
