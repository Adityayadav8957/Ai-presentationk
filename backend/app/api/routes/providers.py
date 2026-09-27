from fastapi import APIRouter

from app.core.config import get_settings
from app.providers.llm.catalog import list_models

router = APIRouter(prefix="/providers", tags=["providers"])

_LLM_LABELS = {
    "siliconflow": "SiliconFlow",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "ollama": "Ollama (offline / local)",
}


@router.get("")
def list_providers():
    settings = get_settings()

    configured_by_name = {
        "siliconflow": bool(settings.siliconflow_api_key),
        "openai": bool(settings.openai_api_key),
        "anthropic": bool(settings.anthropic_api_key),
        "ollama": True,
    }

    llm = [
        {
            "name": name,
            "label": label,
            "configured": configured_by_name[name],
            "models": list_models(name) if configured_by_name[name] else [],
        }
        for name, label in _LLM_LABELS.items()
    ]

    return {
        "llm": llm,
        "image": [
            {
                "name": "siliconflow",
                "label": "SiliconFlow",
                "configured": bool(settings.siliconflow_api_key),
            },
            {"name": "pollinations", "label": "Pollinations (free)", "configured": True},
        ],
        "defaults": {
            "llm": settings.default_llm_provider,
            "image": settings.default_image_provider,
        },
    }
