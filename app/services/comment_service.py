from datetime import date

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from starlette import status

from app.core.utils import PagePaginator
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import (
    CommentCreate,
    CommentInDB,
    CommentUpdate,
    CommentFilterParams,
    PaginatedComments,
)
from app.schemas.user import UserInDB
from app.celery.tasks import validate_comment_content


class CommentService:
    def __init__(self, comment_repository: CommentRepository) -> None:
        self.repository = comment_repository

    async def get_list(
        self,
        filter_params: CommentFilterParams,
    ) -> PaginatedComments:
        filters = filter_params.model_dump(exclude_none=True, exclude={"page", "limit"})
        paginator = PagePaginator(
            page=filter_params.page,
            limit=filter_params.limit,
            total_records=await self.repository.count_list(**filters),
        )
        comments = await self.repository.get_list(
            offset=paginator.offset,
            limit=paginator.limit,
            **filters,
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
        except IntegrityError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Post with id {comment.post_id} not found",
            ) from e

        validate_comment_content.delay(comment_created.id)
        return comment_created

    async def get_analytics(self, date_from: date, date_to: date) -> dict:
        return await self.repository.get_analytics(date_from, date_to)

    async def get_by_id(self, record_id: int, include_blocked: bool = False) -> CommentInDB:
        comment = await self.repository.get_by_id(record_id)
        if not comment or (comment.is_blocked and not include_blocked):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {record_id} not found",
            )
        return comment

    async def update_by_id(
        self, record_id: int, current_user: UserInDB, comment_update: CommentUpdate
    ) -> CommentInDB:
        comment_to_update = await self.get_by_id(record_id, include_blocked=True)

        if comment_to_update.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

        updated = await self.repository.update_by_id(
            record_id=record_id,
            **comment_update.model_dump(exclude_unset=True),
        )

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
            )

        validate_comment_content.delay(record_id)
        return await self.get_by_id(record_id, include_blocked=True)

    async def delete_by_id(
        self,
        record_id: int,
        current_user: UserInDB,
    ) -> None:
        comment_to_delete = await self.get_by_id(record_id, include_blocked=True)

        if comment_to_delete.owner_id != current_user.id and not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

        deleted = await self.repository.delete_by_id(
            record_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
            )
