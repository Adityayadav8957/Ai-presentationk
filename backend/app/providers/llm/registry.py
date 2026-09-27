from app.core.config import get_settings
from app.providers.llm.anthropic_provider import AnthropicProvider
from app.providers.llm.base import LLMProvider
from app.providers.llm.openai_compatible import OpenAICompatibleProvider

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "siliconflow": "Qwen/Qwen2.5-72B-Instruct",
    "ollama": "llama3.1",
    "anthropic": "claude-sonnet-5",
}


def get_llm_provider(name: str | None = None, model: str | None = None) -> LLMProvider:
    settings = get_settings()
    provider_name = name or settings.default_llm_provider
    resolved_model = model or _DEFAULT_MODELS.get(provider_name)

    if provider_name == "openai":
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key or "",
            base_url=settings.openai_base_url,
            model=resolved_model,
        )
    if provider_name == "siliconflow":
        return OpenAICompatibleProvider(
            api_key=settings.siliconflow_api_key or "",
            base_url=settings.siliconflow_base_url,
            model=resolved_model,
        )
    if provider_name == "ollama":
        return OpenAICompatibleProvider(
            api_key="ollama",
            base_url=settings.ollama_base_url,
            model=resolved_model,
        )
    if provider_name == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key or "", model=resolved_model)

    raise ValueError(f"Unknown LLM provider: {provider_name}")
