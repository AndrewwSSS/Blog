from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import CommentDB
from app.schemas.comment import CommentRead, Comment
from app.schemas.user import UserRead


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_comments(self) -> [CommentRead]:
        query = select(CommentDB)
        cities_list = await self.session.execute(query)
        return [
            CommentRead.model_validate(city[0])
            for city in cities_list.fetchall()
        ]

    async def create_comment(self, comment: Comment, user: UserRead) -> CommentRead:
        comment_db = CommentDB(
            **comment.dict(),
            owner_id=user.id
        )
        self.session.add(comment_db)
        await self.session.commit()
        await self.session.refresh(comment_db)
        return CommentRead.model_validate(
            comment_db
        )



