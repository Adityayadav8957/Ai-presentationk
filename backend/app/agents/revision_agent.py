from app.agents.json_utils import extract_json
from app.agents.slide_planner import SLIDE_SCHEMA_HINT
from app.providers.llm.base import LLMProvider


class RevisionAgent:
    """Handles chat-based edits ('make this more premium', 'shorten slide 5')
    by re-generating the whole deck JSON with the instruction applied. Whole-deck
    replacement is simpler and more reliable than diff-patching individual slides."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, current_slides: list[dict], instruction: str) -> list[dict]:
        prompt = (
            f"Current presentation slides (JSON):\n{current_slides}\n\n"
            f"User instruction: {instruction}\n\n"
            "Apply the instruction and return the complete updated deck — same number of "
            "slides unless the instruction asks to add/remove some.\n"
            f"{SLIDE_SCHEMA_HINT}"
        )
        response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.4)

        try:
            slides = extract_json(response)
            if isinstance(slides, list) and slides:
                return slides
        except ValueError:
            pass

        return current_slides
