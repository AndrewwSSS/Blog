from abc import ABC, abstractmethod
from typing import Iterable, Type

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base_model import BaseModel
from pydantic import BaseModel as PydanticBaseModel


class AsyncDatabaseRepository(ABC):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @abstractmethod
    async def get_by_id(self, id: int) -> Type[BaseModel]:
        ...

    @abstractmethod
    async def get_all(self) -> Iterable[Type[BaseModel]]:
        ...

    @abstractmethod
    async def delete(self, id: int) -> bool | None:
        ...

    @abstractmethod
    async def update(self, id: int, data: Type[PydanticBaseModel]) -> None:
        ...

    @abstractmethod
    async def create(self, data: Type[PydanticBaseModel]) -> Type[BaseModel]:
        ...

    async def count_records(self) -> int:
        ...