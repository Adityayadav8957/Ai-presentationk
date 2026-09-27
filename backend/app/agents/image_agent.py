import logging
from pathlib import Path

from app.core.config import get_settings
from app.providers.image.base import ImageProvider

logger = logging.getLogger(__name__)

MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "media"


class ImageAgent:
    def __init__(self, image_provider: ImageProvider):
        self.image_provider = image_provider

    def run_one(self, slide: dict, presentation_id: str, position: int) -> dict:
        """Generates any missing images for ONE slide. Filenames are keyed by
        (position, element index) rather than a shared counter, so this is
        safe to call concurrently from multiple threads for different slides."""
        settings = get_settings()
        folder = MEDIA_ROOT / presentation_id
        folder.mkdir(parents=True, exist_ok=True)

        for element_index, element in enumerate(slide.get("elements", [])):
            if element.get("type") != "image" or element.get("url"):
                continue
            filename = f"{position}_{element_index}.png"
            prompt = element.get("prompt") or slide.get("title", "presentation slide")
            try:
                image_bytes = self.image_provider.generate(prompt)
                (folder / filename).write_bytes(image_bytes)
                element["url"] = f"{settings.public_backend_url}/media/{presentation_id}/{filename}"
                logger.info("ImageAgent: generated image for slide position=%d", position)
            except Exception as exc:
                logger.warning("ImageAgent: failed to generate image for prompt=%r: %s", prompt, exc)
                element["error"] = str(exc)

        return slide

    def run(self, slides: list[dict], presentation_id: str) -> list[dict]:
        return [self.run_one(slide, presentation_id, position) for position, slide in enumerate(slides)]
