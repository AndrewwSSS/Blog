from abc import ABC
from typing import Iterable, Type

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    update,
    select,
    delete, func
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


    async def get_by_id(self, record_id: int) ->  list[Type[PydanticBaseModel]] | None:
        query = select(self.model).where(self.model.id == record_id)
        result = await self.session.execute(query)
        post_db = result.scalar_one_or_none()
        if post_db:
            return self.pydantic_model.model_validate(post_db)

    async def get_all(self) -> Iterable[Type[BaseModel]]:
        query = select(self.model)

        result = await self.session.execute(query)
        records = result.scalars().all()

        return [
            self.pydantic_model.model_validate(record)
            for record in records
        ]

    async def delete_by_id(self, record_id: int) -> bool | None:
        query = (
            delete(self.model)
            .where(self.model.id == record_id)
        )

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount == 1

    async def update_by_id(self, record_id: int, **fields) -> bool:
        query = (
            update(self.model)
            .where(self.model.id == record_id)
            .values(**fields)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(query)
        await self.session.commit()

        return result.rowcount == 1

    async def create(self, **data) -> Type[BaseModel]:
        record = self.model(
            **data
        )

        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)

        return self.pydantic_model.model_validate(
            record
        )

    async def count_records(self) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model)
        )

        return result.scalar()

    async def get_by_ids(self, records_ids: Iterable[int]) -> Type[BaseModel]:
        query = select(self.model).where(self.model.id.in_(records_ids))
        result = await self.session.execute(query)
        posts_list = result.scalars().all()
        return [
            self.pydantic_model.model_validate(post)
            for post in posts_list
        ]
