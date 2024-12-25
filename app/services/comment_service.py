import logging
from datetime import date

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.core.config import settings
from app.core.utils import PagePaginator
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import (
    CommentCreate,
    CommentInDB,
    CommentUpdate,
    CommentFilterParams, PaginatedComments
)
from app.schemas.comment import CommentRead
from app.schemas.user import UserInDB
from app.celery.tasks import validate_comment_content


logger = logging.getLogger(__name__)


class CommentService:
    def __init__(self, comment_repository: CommentRepository) -> None:
        self.repository = comment_repository

    async def get_list(
        self,
        filter_params: CommentFilterParams,
    ) -> PaginatedComments:
        count_records = await self.repository.count_records()
        paginator = PagePaginator(
            page=filter_params.page,
            limit=filter_params.limit,
            total_records=count_records,
        )
        comments = await self.repository.get_list(
            offset=paginator.offset,
            **filter_params.model_dump(exclude_unset=True, exclude={"page"}),
        )

        return PaginatedComments(
            items=comments,
            total_pages=paginator.total_pages,
            current_page=paginator.page,
            limit=paginator.limit,
        )

    async def create(self, comment: CommentCreate, user: UserInDB) -> CommentInDB:
        try:
            comment_created = await self.repository.create(
                **comment.model_dump(exclude_none=True),
                owner_id=user.id,
            )
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post with id {comment.post_id} not found",
            )

        validate_comment_content.delay(comment_created.id)
        return comment_created

    async def get_analytics(self, date_from: date, date_to: date) -> dict:
        return await self.repository.get_analytics(date_from, date_to)

    async def validate_content(self, comment_id) -> None:
        comment = await self.repository.get_by_id(
            comment_id
        )
        if not comment:
            raise ValueError("Comment not found")
        validator = settings.CONTENT_VALIDATOR_CLASS()
        is_validated = await validator.validate_comment(
            comment.content,
        )
        if not is_validated:
            await self.repository.update_by_id(
                comment.id,
                {"is_blocked": True}
            )
            print(f"Comment: {comment.id} has been blocked")

    async def get_by_id(self, record_id) -> CommentInDB:
        comment = await self.repository.get_by_id(
            record_id
        )
        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {record_id} not found"
            )
        return comment

    async def update_by_id(
        self,
        record_id: int,
        current_user: UserInDB,
        comment_update: CommentUpdate
    ) -> CommentInDB:
        comment_to_update = await self.get_by_id(record_id)

        if comment_to_update.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied"
            )

        updated = await self.repository.update_by_id(
            record_id=record_id,
            **comment_update.model_dump(exclude_unset=True),
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return await self.get_by_id(record_id)

    async def delete_by_id(
        self,
        record_id: int,
        current_user: UserInDB,
    ) -> None:
        comment_to_delete = await self.get_by_id(record_id)

        if comment_to_delete.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied"
            )

        deleted = await self.repository.delete_by_id(
            record_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
            )
