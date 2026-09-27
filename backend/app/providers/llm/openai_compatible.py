from collections.abc import Iterator

from openai import OpenAI

from app.providers.llm.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Covers OpenAI, SiliconFlow, Ollama, DeepSeek, Together — anything
    exposing an OpenAI-shaped /chat/completions endpoint."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, messages: list[dict], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, **kwargs
        )
        return response.choices[0].message.content or ""

    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True, **kwargs
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
