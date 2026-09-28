import logging

from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)

THEMES = {
    "minimal": {"primary": "#111111", "accent": "#2563eb", "background": "#ffffff", "font": "Inter, sans-serif"},
    "executive": {"primary": "#0f172a", "accent": "#0ea5e9", "background": "#f8fafc", "font": "Inter, sans-serif"},
    "editorial": {"primary": "#1c1917", "accent": "#b45309", "background": "#fafaf9", "font": "Georgia, serif"},
    "startup": {"primary": "#020617", "accent": "#f43f5e", "background": "#ffffff", "font": "Inter, sans-serif"},
    "luxury": {"primary": "#1a1a1a", "accent": "#c9a227", "background": "#fdfdfb", "font": "Georgia, serif"},
}

_KEYWORDS = {
    "startup": ("invest", "pitch", "startup", "raise", "funding"),
    "executive": ("executive", "board", "report", "enterprise", "quarterly"),
    "luxury": ("luxury", "premium", "brand"),
    "editorial": ("story", "magazine", "culture", "history"),
}


def design_theme_question(suggested: str) -> dict:
    """The post-planning guided-mode question: confirm/choose the design
    system rather than silently locking in DesignAgent's keyword guess."""
    return {
        "id": "theme",
        "text": "Pick a design direction for this deck",
        "type": "theme_picker",
        "suggested": suggested,
        "options": [{"id": name, "label": name.capitalize(), **tokens} for name, tokens in THEMES.items()],
    }


class DesignAgent:
    """Deterministic theme selection — no LLM call needed for a small, fixed
    set of design systems."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def run(self, slides: list[dict], brief: dict) -> tuple[list[dict], dict]:
        text = str(brief.get("topic", "")).lower()
        theme_name = "minimal"
        for name, keywords in _KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                theme_name = name
                break

        theme = {"name": theme_name, **THEMES[theme_name]}
        logger.info("DesignAgent: selected theme=%s", theme_name)
        return slides, theme
