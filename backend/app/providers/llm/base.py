from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], **kwargs) -> str:
        ...

    @abstractmethod
    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        ...
