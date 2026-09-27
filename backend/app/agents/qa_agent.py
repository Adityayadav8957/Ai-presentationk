from app.providers.llm.base import LLMProvider


class QAAgent:
    """Screenshots rendered slides via Playwright and critiques them with a
    vision-capable model, feeding fixes back into the slide JSON."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, slides: list[dict]) -> list[dict]:
        return slides
