import inspect
import logging
from collections.abc import Callable
from functools import partial
from types import TracebackType
from typing import Any, Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class UnitOfWork:
    """One database transaction, plus work that must wait until it is committed.

    ``async with UnitOfWork(factory) as uow`` commits when the block succeeds and
    rolls back when it raises. Repositories share ``uow.session`` and only flush.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._after_commit: list[Callable[[], Any]] = []

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.commit()
            else:
                await self.rollback()
        finally:
            await self.session.close()

    def after_commit(self, callback: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None:
        """Run ``callback(*args, **kwargs)`` after the next successful commit.

        The callback may be sync or async. It is dropped on rollback. A failing
        callback is logged, not raised: the data is already committed.
        """
        self._after_commit.append(partial(callback, *args, **kwargs))

    async def commit(self) -> None:
        await self.session.commit()
        callbacks, self._after_commit = self._after_commit, []
        for callback in callbacks:
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception(f"After-commit callback {callback.func!r} failed")

    async def rollback(self) -> None:
        self._after_commit.clear()
        await self.session.rollback()
