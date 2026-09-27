from app.providers.llm.base import LLMProvider


class StoryAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, brief: dict, research: dict) -> dict:
        prompt = (
            "Design a slide-by-slide narrative arc for this presentation brief. "
            "Return the story as an ordered list of beats (one idea per slide).\n"
            f"Brief: {brief}\nResearch notes: {research.get('raw', '')}"
        )
        response = self.llm.chat([{"role": "user", "content": prompt}])
        return {"raw": response, "beats": []}
