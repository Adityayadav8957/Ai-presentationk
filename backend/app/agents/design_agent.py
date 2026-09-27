from app.providers.llm.base import LLMProvider


class DesignAgent:
    """Assigns theme tokens (typography, color, spacing) to the deck."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, slides: list[dict], brief: dict) -> list[dict]:
        return slides
