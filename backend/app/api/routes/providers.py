from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def list_providers():
    settings = get_settings()
    return {
        "llm": [
            {"name": "siliconflow", "configured": bool(settings.siliconflow_api_key)},
            {"name": "openai", "configured": bool(settings.openai_api_key)},
            {"name": "anthropic", "configured": bool(settings.anthropic_api_key)},
            {"name": "ollama", "configured": True},
        ],
        "image": [
            {"name": "siliconflow", "configured": bool(settings.siliconflow_api_key)},
            {"name": "pollinations", "configured": True},
        ],
        "defaults": {
            "llm": settings.default_llm_provider,
            "image": settings.default_image_provider,
        },
    }
