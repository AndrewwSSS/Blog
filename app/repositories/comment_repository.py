from sqlalchemy.ext.asyncio import AsyncSession


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
