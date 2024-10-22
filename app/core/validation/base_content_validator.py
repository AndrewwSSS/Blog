from abc import ABC, abstractmethod


class BaseContentValidator(ABC):
    @abstractmethod
    async def validate_post(self, content: str, title: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def validate_comment(self, content: str) -> bool:
        raise NotImplementedError
