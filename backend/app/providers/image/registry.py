from app.core.config import get_settings
from app.providers.image.base import ImageProvider
from app.providers.image.pollinations import PollinationsImageProvider
from app.providers.image.siliconflow import SiliconFlowImageProvider


def get_image_provider(name: str | None = None) -> ImageProvider:
    settings = get_settings()
    provider_name = name or settings.default_image_provider

    if provider_name == "siliconflow":
        return SiliconFlowImageProvider(
            api_key=settings.siliconflow_api_key or "",
            base_url=settings.siliconflow_base_url,
        )
    if provider_name == "pollinations":
        return PollinationsImageProvider()

    raise ValueError(f"Unknown image provider: {provider_name}")
