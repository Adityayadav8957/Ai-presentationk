import logging

from app.agents.json_utils import extract_json
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)

SLIDE_SCHEMA_HINT = """
Return ONLY a JSON array, one object per slide, in this exact schema:
{
  "type": "hero" | "data_story" | "comparison" | "timeline" | "process" | "split" | "grid",
  "title": "string",
  "elements": [
    {"type": "heading", "text": "..."},
    {"type": "text", "text": "..."},
    {"type": "stat", "value": "73%", "label": "..."},
    {"type": "insight", "text": "..."},
    {"type": "chart", "chartType": "line" | "bar" | "donut", "data": [{"label": "...", "value": 0}]},
    {"type": "image", "prompt": "description for an image generator"}
  ]
}
Never include exact pixel positions or sizes — only semantic content.
No prose, no markdown fences, no commentary before or after — JSON array only.
"""


class SlidePlannerAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, brief: dict, story_text: str, slide_count: int) -> list[dict]:
        prompt = (
            f"Presentation brief: {brief}\n\n"
            f"Narrative outline:\n{story_text}\n\n"
            f"Produce exactly {slide_count} slides covering this outline, choosing the best "
            f"slide type and elements for each idea.\n{SLIDE_SCHEMA_HINT}"
        )
        logger.info("SlidePlannerAgent: requesting %d slides", slide_count)
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.4)
        except Exception:
            logger.exception("SlidePlannerAgent: LLM call failed")
            raise

        try:
            slides = extract_json(response)
            if isinstance(slides, list) and slides:
                logger.info("SlidePlannerAgent: parsed %d slides from JSON", len(slides))
                return slides
            logger.warning("SlidePlannerAgent: JSON parsed but was not a non-empty list, falling back")
        except ValueError:
            logger.warning(
                "SlidePlannerAgent: could not parse JSON from model output, falling back. "
                "Raw response (truncated): %r",
                response[:500],
            )

        return self._fallback(story_text, slide_count)

    def _fallback(self, story_text: str, slide_count: int) -> list[dict]:
        lines = [line.strip("-• ") for line in story_text.splitlines() if line.strip()]
        lines = lines[:slide_count] or ["Untitled"]
        return [
            {"type": "hero", "title": line, "elements": [{"type": "text", "text": line}]}
            for line in lines
        ]
