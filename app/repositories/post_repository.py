from sqlalchemy.ext.asyncio import AsyncSession


class PostRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
