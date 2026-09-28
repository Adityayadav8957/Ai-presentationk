import logging

from app.agents.json_utils import extract_json
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
You are a presentation requirements agent. Given a user's raw request for a
presentation, decide whether there is genuinely important missing
information that would meaningfully change what gets generated — mainly:
who the audience is, what the goal is (inform / persuade / teach / sell /
report), and how long the deck should be.

If the request already makes these reasonably clear (or they're not really
ambiguous for this topic), return no questions — most requests do NOT need
clarification, only ask when it would truly change the output.

Return ONLY JSON in this exact shape, no prose, no markdown fences:
{
  "questions": [
    {"id": "audience", "text": "Who is this presentation for?", "options": ["Investors", "Executives", "Students", "General audience"]},
    {"id": "objective", "text": "What should it accomplish?", "options": ["Inform", "Persuade", "Teach", "Sell"]}
  ]
}
Use short, concrete option lists (3-4 options) grounded in the actual topic
— not generic placeholders. Omit "options" for a question that doesn't fit
multiple-choice. Return {"questions": []} if nothing needs asking.
"""


class RequirementsAgent:
    """Runs once, synchronously, before any Celery job starts — cheap
    enough that a slow/failed call just means no questions get asked
    rather than blocking generation."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, brief: dict) -> list[dict]:
        prompt = f"{INSTRUCTIONS}\n\nUser's request: {brief.get('topic', '')}"
        try:
            response = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.3)
            data = extract_json(response)
            # Be lenient about shape: some models return the bare array
            # instead of the {"questions": [...]} wrapper we asked for.
            if isinstance(data, list):
                questions = data
            elif isinstance(data, dict):
                questions = data.get("questions", [])
            else:
                questions = []
            if isinstance(questions, list):
                return questions
        except Exception as exc:
            logger.warning("RequirementsAgent: failed, skipping clarification: %s", exc)
        return []
