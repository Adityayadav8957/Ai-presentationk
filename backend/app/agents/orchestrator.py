import logging
import re
from collections.abc import Callable

from app.agents.design_agent import DesignAgent
from app.agents.research_agent import ResearchAgent
from app.agents.slide_planner import SlidePlannerAgent
from app.agents.story_agent import StoryAgent
from app.providers.llm.registry import get_llm_provider

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None]


def _extract_slide_count(brief: dict, default: int = 8) -> int:
    # Check the guided-mode "length" clarification answer first (e.g.
    # "Short (5-7 slides)") — it's a deliberate user choice, more
    # trustworthy than guessing from the raw topic text.
    clarified_length = str(brief.get("clarifications", {}).get("length", ""))
    match = re.search(r"(\d+)\+?\s*[-\s]?(?:to\s*)?(\d+)?\+?\s*slide", clarified_length, re.IGNORECASE)
    if match:
        numbers = [int(n) for n in match.groups() if n]
        return max(3, min(round(sum(numbers) / len(numbers)), 20))

    text = str(brief.get("topic", ""))
    match = re.search(r"(\d+)\s*[-\s]?slide", text, re.IGNORECASE)
    if match:
        return max(3, min(int(match.group(1)), 20))
    return default


class Orchestrator:
    """Runs only the sequential planning pipeline (research → story → bare
    slide JSON → theme). Slides come back with no images or HTML yet —
    that part runs afterwards, in parallel and checkpointed per slide, in
    app.worker.slide_pipeline, since it needs database ids and benefits
    from concurrency that planning (each step depends on the last) does
    not."""

    def __init__(self, llm_provider_name: str | None = None, llm_model_name: str | None = None):
        self.llm = get_llm_provider(llm_provider_name, llm_model_name)
        self.research_agent = ResearchAgent(self.llm)
        self.story_agent = StoryAgent(self.llm)
        self.slide_planner = SlidePlannerAgent(self.llm)
        self.design_agent = DesignAgent(self.llm)

    def run(self, brief: dict, on_progress: ProgressCallback | None = None) -> dict:
        def report(step: str) -> None:
            if on_progress:
                on_progress(step)

        slide_count = _extract_slide_count(brief)
        logger.info("Orchestrator: starting planning, slide_count=%d", slide_count)

        report("understanding")
        research = self.research_agent.run(brief)

        report("story_building")
        story = self.story_agent.run(brief, research, slide_count)

        report("slide_planning")
        slides = self.slide_planner.run(brief, story, slide_count)

        report("designing")
        slides, theme = self.design_agent.run(slides, brief)

        logger.info("Orchestrator: planning complete (%d slides)", len(slides))
        return {"story": story, "research": research, "slides": slides, "theme": theme}
