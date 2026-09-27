from app.providers.llm.base import LLMProvider


class ResearchAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, brief: dict) -> dict:
        prompt = (
            "You are a research agent for a presentation generator. Given this brief, "
            "list the factual claims that will be needed, each with a plausible source "
            f"and confidence level.\nBrief: {brief}"
        )
        response = self.llm.chat([{"role": "user", "content": prompt}])
        return {"raw": response, "claims": []}
