from collections.abc import Callable

from app.agents.design_agent import DesignAgent
from app.agents.qa_agent import QAAgent
from app.agents.research_agent import ResearchAgent
from app.agents.slide_planner import SlidePlannerAgent
from app.agents.story_agent import StoryAgent
from app.providers.llm.registry import get_llm_provider

ProgressCallback = Callable[[str], None]


class Orchestrator:
    def __init__(self, llm_provider_name: str | None = None):
        self.llm = get_llm_provider(llm_provider_name)
        self.research_agent = ResearchAgent(self.llm)
        self.story_agent = StoryAgent(self.llm)
        self.slide_planner = SlidePlannerAgent(self.llm)
        self.design_agent = DesignAgent(self.llm)
        self.qa_agent = QAAgent(self.llm)

    def run(self, brief: dict, on_progress: ProgressCallback | None = None) -> dict:
        def report(step: str) -> None:
            if on_progress:
                on_progress(step)

        report("understanding")
        research = self.research_agent.run(brief)

        report("story_building")
        story = self.story_agent.run(brief, research)

        report("slide_planning")
        slides = self.slide_planner.run(story)

        report("designing")
        slides = self.design_agent.run(slides, brief)

        report("qa")
        slides = self.qa_agent.run(slides)

        return {"story": story, "research": research, "slides": slides}
