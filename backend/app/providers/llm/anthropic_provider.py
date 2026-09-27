from collections.abc import Iterator

from anthropic import Anthropic

from app.providers.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict], **kwargs) -> str:
        system = kwargs.pop("system", None)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 4096),
            system=system,
            messages=messages,
            **kwargs,
        )
        return "".join(block.text for block in response.content if block.type == "text")

    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        system = kwargs.pop("system", None)
        with self.client.messages.stream(
            model=self.model,
            max_tokens=kwargs.pop("max_tokens", 4096),
            system=system,
            messages=messages,
            **kwargs,
        ) as stream:
            yield from stream.text_stream
