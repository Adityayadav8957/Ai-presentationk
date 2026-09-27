from pathlib import Path

from app.core.config import get_settings
from app.providers.image.base import ImageProvider

MEDIA_ROOT = Path(__file__).resolve().parent.parent.parent / "media"


class ImageAgent:
    def __init__(self, image_provider: ImageProvider):
        self.image_provider = image_provider

    def run(self, slides: list[dict], presentation_id: str) -> list[dict]:
        settings = get_settings()
        folder = MEDIA_ROOT / presentation_id
        folder.mkdir(parents=True, exist_ok=True)

        counter = 0
        for slide in slides:
            for element in slide.get("elements", []):
                if element.get("type") != "image" or element.get("url"):
                    continue
                counter += 1
                filename = f"{counter}.png"
                try:
                    image_bytes = self.image_provider.generate(
                        element.get("prompt") or slide.get("title", "presentation slide")
                    )
                    (folder / filename).write_bytes(image_bytes)
                    element["url"] = f"{settings.public_backend_url}/media/{presentation_id}/{filename}"
                except Exception as exc:
                    element["error"] = str(exc)

        return slides
