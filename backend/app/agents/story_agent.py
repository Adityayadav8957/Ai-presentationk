from app.providers.llm.base import LLMProvider


class StoryAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, brief: dict, research: dict, slide_count: int) -> str:
        prompt = (
            "You are a presentation storytelling agent. Given this brief and research "
            f"notes, write a {slide_count}-line narrative outline — one short idea per "
            "line, in the order slides should appear, building toward a clear conclusion. "
            "Plain text only, one idea per line, no numbering, no extra commentary.\n"
            f"Brief: {brief}\nResearch notes: {research.get('raw', '')}"
        )
        return self.llm.chat([{"role": "user", "content": prompt}], temperature=0.6)
