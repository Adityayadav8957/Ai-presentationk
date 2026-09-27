import logging
import re
from concurrent.futures import ThreadPoolExecutor

from app.agents.design_reference import AVOID_LIST, DESIGN_PRINCIPLES, pick_example
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)

HTML_INSTRUCTIONS = """
You are a presentation slide designer. Generate a single self-contained HTML
fragment for ONE slide of a presentation deck.

Technical rules:
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
  they are not defined anywhere. Make sure text color always has strong
  contrast against its own background.
- Only include an <img> tag if this slide's content JSON has an element
  with "type": "image" AND a non-empty "url" field — then use that EXACT
  url. Never invent, fabricate, or use placeholder/example.com image URLs.
  If there is no such element, do not add any <img> tag at all.
- If this slide has a "chart" element with real data, render it as an
  actual inline <svg> (bars/lines positioned from the real values given) —
  never a text placeholder box.
- Use the given slide "type" as a loose layout hint: hero = one big
  statement; data_story = a headline plus a supporting stat/chart region;
  comparison = two or more columns/sides; timeline/process = a genuine
  sequence (this is the one case where a rule line or ordered markers are
  appropriate); split = an uneven two-region layout; grid = a card layout.
- Never let content overflow its container.
- Never set a text element's color to the same color as the background
  behind it — always keep strong contrast. Double-check this before
  finishing.
- Do not rotate or transform text elements (no `transform: rotate(...)`
  on headings, stats, or body text) — keep all text horizontal and legible.

The technique example below is inspiration for COMPOSITION ONLY. Copying
its actual sentences, numbers, or exact color choices is a failure — you
must write entirely new text and values for this slide's real content.
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
    known — there's no sequential dependency between slides. Different
    slides are shown different technique examples so a whole deck doesn't
    converge on one repeated layout."""

    def __init__(self, llm: LLMProvider, max_workers: int = 4):
        self.llm = llm
        self.max_workers = max_workers

    def render_one(self, index: int, slide: dict, theme: dict, brief: dict) -> dict:
        example = pick_example(slide.get("type", ""), index)
        prompt = (
            f"{HTML_INSTRUCTIONS}\n\n"
            f"{DESIGN_PRINCIPLES}\n\n"
            f"{AVOID_LIST}\n\n"
            f"Below is ONE technique reference showing the level of visual craft "
            f"expected (composition: {example['name']}). This is inspiration for "
            f"technique only — invent your own composition for this slide's actual "
            f"content, do not reuse this layout or its text verbatim:\n"
            f"{example['html']}\n\n"
            f"Deck topic: {brief.get('topic', '')}\n"
            f"Theme (use these exact colors/font): {theme}\n\n"
            f"This slide's content (JSON): {slide}\n\n"
            "Generate the HTML fragment now."
        )
        try:
            raw = self.llm.chat([{"role": "user", "content": prompt}], temperature=0.7)
            html = _strip_fences(raw)
            logger.info("HTMLAgent: rendered slide %r (%d chars)", slide.get("title"), len(html))
            return {**slide, "html": html}
        except Exception as exc:
            logger.warning("HTMLAgent: failed to render slide %r: %s — using fallback layout", slide.get("title"), exc)
            return slide

    def run(self, slides: list[dict], theme: dict, brief: dict) -> list[dict]:
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            return list(
                pool.map(
                    lambda pair: self.render_one(pair[0], pair[1], theme, brief),
                    enumerate(slides),
                )
            )
