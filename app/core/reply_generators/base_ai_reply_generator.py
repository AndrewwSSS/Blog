from abc import ABC
from abc import abstractmethod


class BaseAIReplyGenerator(ABC):
    @abstractmethod
    def generate_post_reply(self, title: str, content: str) -> str:
        raise NotImplementedError
