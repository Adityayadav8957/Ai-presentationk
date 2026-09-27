import base64

import httpx

from app.providers.image.base import ImageProvider


class SiliconFlowImageProvider(ImageProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "black-forest-labs/FLUX.1-schnell",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, **kwargs) -> bytes:
        response = httpx.post(
            f"{self.base_url}/images/generations",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "prompt": prompt,
                # Valid enum per SiliconFlow's API: 512x512, 768x1024, 1024x768,
                # 576x1024, 1024x576 — "1024x1024" is NOT accepted.
                "image_size": kwargs.get("image_size", "1024x576"),
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()["data"][0]
        if "b64_json" in data:
            return base64.b64decode(data["b64_json"])
        return httpx.get(data["url"], timeout=60).content
