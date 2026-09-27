from app.providers.llm.base import LLMProvider


class SlidePlannerAgent:
    """Turns story beats into semantic slide JSON — never pixel coordinates.
    The frontend layout engine owns geometry."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, story: dict) -> list[dict]:
        prompt = (
            "Convert this story into a list of slides. For each slide, output a semantic "
            "JSON object with a 'type' (e.g. hero, data_story, comparison, timeline, process) "
            "and an 'elements' list describing what content it needs — never exact positions "
            f"or pixel sizes.\nStory: {story.get('raw', '')}"
        )
        self.llm.chat([{"role": "user", "content": prompt}])
        return []
