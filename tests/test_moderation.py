import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import tasks
from app.core.validation.base_content_validator import BaseContentValidator
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.outbox_repository import OutboxRepository
from app.schemas.comment import CommentInDB, CommentUpdate
from app.schemas.post import PostInDB, PostUpdate
from app.schemas.user import UserInDB
from app.services import moderation
from app.services.comment_service import CommentService
from app.services.post_service import PostService
from app.db.unit_of_work import UnitOfWork
from tests.conftest import SentTask
from tests.fixtures import (
    async_session_maker,
    create_comment,
    create_post,
)


class AcceptAllValidator(BaseContentValidator):
    async def validate_post(self, content: str, title: str) -> bool:
        return True

    async def validate_comment(self, content: str) -> bool:
        return True


class RejectAllValidator(BaseContentValidator):
    async def validate_post(self, content: str, title: str) -> bool:
        return False

    async def validate_comment(self, content: str) -> bool:
        return False


@pytest.fixture
def fake_tasks(sent_tasks: list[SentTask]) -> "TaskCalls":
    return TaskCalls(sent_tasks)


class TaskCalls:
    """Args of each sent Celery task, looked up by the task's function name."""

    def __init__(self, sent: list[SentTask]) -> None:
        self.sent = sent

    def __getitem__(self, task: str) -> list[tuple]:
        return [t.args for t in self.sent if t.short_name == task]


async def block_post(session: AsyncSession, post_id: int) -> None:
    await PostRepository(session).update_by_id(post_id, is_blocked=True)


async def block_comment(session: AsyncSession, comment_id: int) -> None:
    await CommentRepository(session).update_by_id(comment_id, is_blocked=True)


async def test_validate_post_blocks_and_unblocks(
    test_post: PostInDB,
    session: AsyncSession,
    uow: UnitOfWork,
    monkeypatch,
):
    repository = PostRepository(session)

    monkeypatch.setattr(moderation, "get_content_validator", RejectAllValidator)
    await moderation.moderate_post(repository, uow, test_post.id)
    assert (await repository.get_by_id(test_post.id)).is_blocked is True

    monkeypatch.setattr(moderation, "get_content_validator", AcceptAllValidator)
    await moderation.moderate_post(repository, uow, test_post.id)
    assert (await repository.get_by_id(test_post.id)).is_blocked is False


async def test_validate_comment_blocks_and_unblocks(
    test_comment: CommentInDB,
    session: AsyncSession,
    monkeypatch,
):
    repository = CommentRepository(session)

    monkeypatch.setattr(moderation, "get_content_validator", RejectAllValidator)
    await moderation.moderate_comment(repository, test_comment.id)
    assert (await repository.get_by_id(test_comment.id)).is_blocked is True

    monkeypatch.setattr(moderation, "get_content_validator", AcceptAllValidator)
    await moderation.moderate_comment(repository, test_comment.id)
    assert (await repository.get_by_id(test_comment.id)).is_blocked is False


async def test_blocked_post_is_hidden_from_reads(
    test_user: UserInDB,
    session: AsyncSession,
    uow: UnitOfWork,
):
    visible = await create_post(test_user.id)
    blocked = await create_post(test_user.id)
    await block_post(session, blocked.id)
    service = PostService(PostRepository(session), OutboxRepository(session), uow)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_by_id(blocked.id)
    assert exc_info.value.status_code == 404

    listed_ids = [post.id for post in await PostRepository(session).get_list()]
    assert listed_ids == [visible.id]


async def test_owner_can_update_and_delete_blocked_post(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
    uow: UnitOfWork,
    fake_tasks: TaskCalls,
):
    await block_post(session, test_post.id)
    service = PostService(PostRepository(session), OutboxRepository(session), uow)

    updated = await service.update_by_id(test_post.id, PostUpdate(content="edited"), test_user)
    assert updated.content == "edited"
    assert fake_tasks["validate_post_content"] == []
    await uow.commit()
    assert fake_tasks["validate_post_content"] == [(test_post.id,)]

    await service.delete_by_id(test_post.id, test_user)
    await uow.commit()
    assert await PostRepository(session).get_by_id(test_post.id) is None
    assert fake_tasks["delete_post_document"] == [(test_post.id,)]


async def test_blocked_comment_is_hidden_from_reads(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
    uow: UnitOfWork,
):
    visible = await create_comment(test_user.id, test_post.id)
    blocked = await create_comment(test_user.id, test_post.id)
    await block_comment(session, blocked.id)
    service = CommentService(CommentRepository(session), OutboxRepository(session), uow)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_by_id(blocked.id)
    assert exc_info.value.status_code == 404

    listed = await CommentRepository(session).get_list(post_id=test_post.id)
    assert [comment.id for comment in listed] == [visible.id]


async def test_comment_update_requeues_moderation(
    test_user: UserInDB,
    test_comment: CommentInDB,
    session: AsyncSession,
    uow: UnitOfWork,
    fake_tasks: TaskCalls,
):
    await block_comment(session, test_comment.id)
    service = CommentService(CommentRepository(session), OutboxRepository(session), uow)

    updated = await service.update_by_id(
        test_comment.id, test_user, CommentUpdate(content="edited")
    )

    assert updated.content == "edited"
    await uow.commit()
    assert fake_tasks["validate_comment_content"] == [(test_comment.id,)]


async def test_search_skips_blocked_posts(
    test_user: UserInDB,
    session: AsyncSession,
    monkeypatch,
):
    visible = await create_post(test_user.id)
    blocked = await create_post(test_user.id)
    await block_post(session, blocked.id)

    class FakeElasticsearchClient:
        async def search_by_template(self, **kwargs) -> dict:
            return {"hits": {"hits": [{"_id": str(blocked.id)}, {"_id": str(visible.id)}]}}

    monkeypatch.setattr(
        "app.repositories.post_repository.AsyncElasticsearchClient",
        FakeElasticsearchClient,
    )

    results = await PostRepository(session).search("anything")

    assert [post.id for post in results] == [visible.id]


async def test_auto_reply_creates_comment(
    test_post: PostInDB,
    session: AsyncSession,
    monkeypatch,
):
    class FakeReplyGenerator:
        async def generate_post_reply(self, title: str, content: str) -> str:
            return "auto reply"

    monkeypatch.setattr(tasks, "async_session", async_session_maker)
    monkeypatch.setattr(tasks, "get_reply_generator", FakeReplyGenerator)

    await tasks._create_reply_for_post(test_post.id)

    comments = await CommentRepository(session).get_list(post_id=test_post.id)
    assert [(c.content, c.owner_id) for c in comments] == [("auto reply", test_post.owner_id)]
