import logging
import re
from concurrent.futures import ThreadPoolExecutor

from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)

HTML_INSTRUCTIONS = """
You are a presentation slide designer. Generate a single self-contained HTML
fragment for ONE slide of a presentation deck.

Rules:
- Output ONLY the HTML fragment (one root <div>...</div>), no markdown
  fences, no <html>/<head>/<body> tags, no <script> tags.
- The root element and everything inside it must size itself with
  width:100%; height:100% of its container (assume a 16:9 canvas) — never
  hardcode pixel dimensions like 1280x720, since this gets scaled to fit
  different containers.
- Style with an inline <style> block scoped to a unique class name you
  invent, or inline style attributes. Do not reference Tailwind, Bootstrap,
  or any external stylesheet/font — everything must be self-contained.
- Use the theme's colors and font given below as their LITERAL values
  (e.g. `color: #2563eb;`) — do not use CSS variables like `var(--accent)`,
  they are not defined anywhere. Use them consistently so every slide in
  the deck looks like part of the same design system, and make sure text
  color always has strong contrast against its own background.
- Use large, confident typography and generous whitespace — this is a
  premium/professional slide, not a text document. Avoid walls of text;
  favor a few strong statements, a stat, or a short list over paragraphs.
- Only include an <img> tag if this slide's content JSON has an element
  with "type": "image" AND a non-empty "url" field — then use that EXACT
  url. Never invent, fabricate, or use placeholder/example.com image URLs.
  If there is no such element, do not add any <img> tag at all.
- Use the given slide "type" as a layout hint: hero = one big centered
  statement; data_story = a headline plus a supporting stat/chart region;
  comparison = two or more columns; timeline = a horizontal/vertical
  progression; process = sequential numbered steps; split = a ~60/40
  two-region layout; grid = a card grid.
- Never let content overflow its container.
"""


def _strip_fences(text: str) -> str:
    match = re.search(r"```(?:html)?\s*(.*?)```", text, re.DOTALL)
    html = match.group(1).strip() if match else text.strip()
    # Belt-and-suspenders: the prompt forbids <script>, but never trust model
    # output outright — strip it if it slips through.
    return re.sub(r"<script\b.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)


class HTMLAgent:
    """Turns each slide's semantic content + the deck's shared theme into a
    real, styled HTML fragment. Runs one LLM call per slide, in parallel,
    since by this point every slide's content and the theme are already
    known — there's no sequential dependency between slides."""

    def __init__(self, llm: LLMProvider, max_workers: int = 4):
        self.llm = llm
        self.max_workers = max_workers

    def _render_one(self, slide: dict, theme: dict, brief: dict) -> dict:
        prompt = (
            f"{HTML_INSTRUCTIONS}\n\n"
            f"Deck topic: {brief.get('topic', '')}\n"
            f"Theme: {theme}\n\n"
            f"This slide's content (JSON): {slide}\n\n"
            "Generate the HTML fragment now."
        )
        try:
            raw = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.5)
            html = _strip_fences(raw)
            logger.info("HTMLAgent: rendered slide %r (%d chars)", slide.get("title"), len(html))
            return {**slide, "html": html}
        except Exception as exc:
            logger.warning("HTMLAgent: failed to render slide %r: %s — using fallback layout", slide.get("title"), exc)
            return slide

    def run(self, slides: list[dict], theme: dict, brief: dict) -> list[dict]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(pool.map(lambda s: self._render_one(s, theme, brief), slides))
