from urllib.parse import quote

import httpx

from app.providers.image.base import ImageProvider


class PollinationsImageProvider(ImageProvider):
    """Free, keyless fallback image provider."""

    def generate(self, prompt: str, **kwargs) -> bytes:
        width = kwargs.get("width", 1024)
        height = kwargs.get("height", 576)
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        response = httpx.get(
            url, params={"width": width, "height": height, "nologo": "true"}, timeout=60
        )
        response.raise_for_status()
        return response.content
