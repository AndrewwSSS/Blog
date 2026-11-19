from abc import ABC
from typing import Iterable, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    update,
    select,
    delete,
)
from app.db.base_model import BaseModel
from pydantic import BaseModel as PydanticBaseModel


class AsyncDatabaseRepository(ABC):
    model: Type[BaseModel]
    pydantic_model: Type[PydanticBaseModel]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

        if not self.pydantic_model:
            raise TypeError("pydantic model not defined")

        if not self.model:
            raise TypeError("model not defined")

    async def get_by_id(self, record_id: int) -> list[Type[PydanticBaseModel]] | None:
        query = select(self.model).where(self.model.id == record_id)
        result = await self.session.execute(query)
        post_db = result.scalar_one_or_none()
        if post_db:
            return self.pydantic_model.model_validate(post_db)

    async def delete_by_id(self, record_id: int) -> bool | None:
        query = delete(self.model).where(self.model.id == record_id)

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount == 1

    async def update_by_id(self, record_id: int, commit: bool = True, **fields) -> bool:
        query = (
            update(self.model)
            .where(self.model.id == record_id)
            .values(**fields)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(query)
        if commit:
            await self.session.commit()

        return result.rowcount == 1

    async def create(self, commit: bool = True, **data) -> Type[BaseModel]:
        """Insert a record. With commit=False it is only flushed (it gets an id),
        so the caller can add more changes and commit them together."""
        record = self.model(**data)

        self.session.add(record)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        await self.session.refresh(record)

        return self.pydantic_model.model_validate(record)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def get_by_ids(self, records_ids: Iterable[int]) -> Type[BaseModel]:
        query = select(self.model).where(self.model.id.in_(records_ids))
        result = await self.session.execute(query)
        posts_list = result.scalars().all()
        return [self.pydantic_model.model_validate(post) for post in posts_list]
