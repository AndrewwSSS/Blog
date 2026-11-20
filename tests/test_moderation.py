import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery import tasks
from app.core.validation.base_content_validator import BaseContentValidator
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.schemas.comment import CommentInDB, CommentUpdate
from app.schemas.post import PostInDB, PostUpdate
from app.schemas.user import UserInDB
from app.services import comment_service, moderation, post_service
from app.services.comment_service import CommentService
from app.services.post_service import PostService
from app.db.unit_of_work import UnitOfWork
from tests.fixtures import (
    async_session_maker,
    create_comment,
    create_post,
)


class FakeTask:
    def __init__(self) -> None:
        self.calls = []

    def delay(self, *args) -> None:
        self.calls.append(args)

    def apply_async(self, args=(), **kwargs) -> None:
        self.calls.append(tuple(args))


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


@pytest.fixture(autouse=True)
def fake_tasks(monkeypatch) -> dict[str, FakeTask]:
    fakes = {}
    for module, names in (
        (
            post_service,
            (
                "create_reply_for_post",
                "validate_post_content",
                "add_post_to_elastic_search",
                "update_post_document",
                "delete_post_document",
            ),
        ),
        (comment_service, ("validate_comment_content",)),
    ):
        for name in names:
            fakes[name] = FakeTask()
            monkeypatch.setattr(module, name, fakes[name])
    return fakes


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
):
    visible = await create_post(test_user.id)
    blocked = await create_post(test_user.id)
    await block_post(session, blocked.id)
    service = PostService(PostRepository(session))

    with pytest.raises(HTTPException) as exc_info:
        await service.get_by_id(blocked.id)
    assert exc_info.value.status_code == 404

    listed_ids = [post.id for post in await PostRepository(session).get_list()]
    assert listed_ids == [visible.id]


async def test_owner_can_update_and_delete_blocked_post(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
    fake_tasks: dict[str, FakeTask],
):
    await block_post(session, test_post.id)
    service = PostService(PostRepository(session))

    updated = await service.update_by_id(test_post.id, PostUpdate(content="edited"), test_user)
    assert updated.content == "edited"
    assert fake_tasks["validate_post_content"].calls == [(test_post.id,)]

    await service.delete_by_id(test_post.id, test_user)
    assert await PostRepository(session).get_by_id(test_post.id) is None


async def test_blocked_comment_is_hidden_from_reads(
    test_user: UserInDB,
    test_post: PostInDB,
    session: AsyncSession,
):
    visible = await create_comment(test_user.id, test_post.id)
    blocked = await create_comment(test_user.id, test_post.id)
    await block_comment(session, blocked.id)
    service = CommentService(CommentRepository(session))

    with pytest.raises(HTTPException) as exc_info:
        await service.get_by_id(blocked.id)
    assert exc_info.value.status_code == 404

    listed = await CommentRepository(session).get_list(post_id=test_post.id)
    assert [comment.id for comment in listed] == [visible.id]


async def test_comment_update_requeues_moderation(
    test_user: UserInDB,
    test_comment: CommentInDB,
    session: AsyncSession,
    fake_tasks: dict[str, FakeTask],
):
    await block_comment(session, test_comment.id)
    service = CommentService(CommentRepository(session))

    updated = await service.update_by_id(
        test_comment.id, test_user, CommentUpdate(content="edited")
    )

    assert updated.content == "edited"
    assert fake_tasks["validate_comment_content"].calls == [(test_comment.id,)]


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
