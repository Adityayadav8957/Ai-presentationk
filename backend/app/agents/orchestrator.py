import re
from collections.abc import Callable

from app.agents.design_agent import DesignAgent
from app.agents.image_agent import ImageAgent
from app.agents.research_agent import ResearchAgent
from app.agents.slide_planner import SlidePlannerAgent
from app.agents.story_agent import StoryAgent
from app.providers.image.registry import get_image_provider
from app.providers.llm.registry import get_llm_provider

ProgressCallback = Callable[[str], None]


def _extract_slide_count(brief: dict, default: int = 8) -> int:
    text = str(brief.get("topic", ""))
    match = re.search(r"(\d+)\s*[-\s]?slide", text, re.IGNORECASE)
    if match:
        return max(3, min(int(match.group(1)), 20))
    return default


class Orchestrator:
    """Runs the content-planning pipeline (research → story → slides →
    theme → images). Persistence and visual QA happen afterwards in the
    Celery task, since QA needs slides to already have database ids."""

    def __init__(
        self,
        llm_provider_name: str | None = None,
        llm_model_name: str | None = None,
        image_provider_name: str | None = None,
    ):
        self.llm = get_llm_provider(llm_provider_name, llm_model_name)
        self.research_agent = ResearchAgent(self.llm)
        self.story_agent = StoryAgent(self.llm)
        self.slide_planner = SlidePlannerAgent(self.llm)
        self.design_agent = DesignAgent(self.llm)
        self.image_agent = ImageAgent(get_image_provider(image_provider_name))

    def run(self, brief: dict, presentation_id: str, on_progress: ProgressCallback | None = None) -> dict:
        def report(step: str) -> None:
            if on_progress:
                on_progress(step)

        slide_count = _extract_slide_count(brief)

        report("understanding")
        research = self.research_agent.run(brief)

        report("story_building")
        story = self.story_agent.run(brief, research, slide_count)

        report("slide_planning")
        slides = self.slide_planner.run(brief, story, slide_count)

        report("designing")
        slides, theme = self.design_agent.run(slides, brief)

        report("image_generation")
        slides = self.image_agent.run(slides, presentation_id)

        return {"story": story, "research": research, "slides": slides, "theme": theme}
