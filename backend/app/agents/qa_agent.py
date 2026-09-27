import base64

from app.agents.json_utils import extract_json
from app.providers.llm.base import LLMProvider
from app.rendering.qa_screenshot import screenshot_slide

QA_PROMPT = (
    "You are a presentation design QA reviewer. Look at this slide screenshot and "
    'report issues as JSON only: {"issues": ["..."], "passed": true|false}. Check for '
    "text overflow, overlap, tiny/unreadable text, crowding, and poor visual hierarchy."
)


class QAAgent:
    """Screenshots the rendered slide (via the frontend's own render route) and
    asks a vision-capable model to critique it. Never blocks the pipeline —
    a failed screenshot or vision call just gets recorded as skipped."""

    def __init__(self, vision_llm: LLMProvider):
        self.vision_llm = vision_llm

    def review(self, presentation_id: str, slide_id: str) -> dict:
        try:
            image_bytes = screenshot_slide(presentation_id, slide_id)
        except Exception as exc:
            return {"skipped": True, "reason": f"screenshot failed: {exc}"}

        b64 = base64.b64encode(image_bytes).decode()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": QA_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }
        ]

        try:
            response = self.vision_llm.chat(messages)
        except Exception as exc:
            return {"skipped": True, "reason": f"vision call failed: {exc}"}

        try:
            return extract_json(response)
        except ValueError:
            return {"skipped": True, "reason": "could not parse QA response", "raw": response}
