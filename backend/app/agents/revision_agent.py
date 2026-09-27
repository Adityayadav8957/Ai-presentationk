import logging

from app.agents.json_utils import extract_json
from app.agents.slide_planner import SLIDE_SCHEMA_HINT
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)


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
        logger.info("RevisionAgent: applying instruction=%r to %d slides", instruction, len(current_slides))
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.4)
        except Exception:
            logger.exception("RevisionAgent: LLM call failed")
            raise

        try:
            slides = extract_json(response)
            if isinstance(slides, list) and slides:
                logger.info("RevisionAgent: parsed %d revised slides", len(slides))
                return slides
            logger.warning("RevisionAgent: JSON parsed but was not a non-empty list, keeping original slides")
        except ValueError:
            logger.warning(
                "RevisionAgent: could not parse JSON from model output, keeping original slides. "
                "Raw response (truncated): %r",
                response[:500],
            )

        return current_slides
