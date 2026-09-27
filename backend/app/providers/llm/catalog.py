from app.providers.llm.ollama_utils import list_pulled_models
from app.providers.llm.registry import get_llm_provider

_FALLBACK_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4.1-mini"],
    "siliconflow": [
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-32B-Instruct",
        "Qwen/Qwen2.5-7B-Instruct",
        "deepseek-ai/DeepSeek-V2.5",
        "THUDM/glm-4-9b-chat",
    ],
    "anthropic": ["claude-sonnet-5", "claude-opus-5-5", "claude-haiku-4-5-20251001"],
}

_SUGGESTED_OLLAMA_MODELS = ["llama3.2:3b", "llama3.1:8b", "qwen2.5:7b", "mistral:7b", "llava:7b"]


def list_models(provider_name: str) -> list[dict]:
    """Best-effort model listing, unified as [{"id": ..., "ready": bool}].
    'ready' means usable immediately. For Ollama, a not-yet-pulled model is
    still listed (so it can be selected) but marked not ready — selecting it
    triggers a pull before generation starts (see ollama_utils.ensure_model_pulled)."""
    if provider_name == "ollama":
        pulled = list_pulled_models()
        pulled_set = set(pulled)
        suggested = [m for m in _SUGGESTED_OLLAMA_MODELS if m not in pulled_set]
        return [{"id": m, "ready": True} for m in pulled] + [
            {"id": m, "ready": False} for m in suggested
        ]

    ids: list[str] = []
    try:
        provider = get_llm_provider(provider_name)
        client = getattr(provider, "client", None)
        if client is not None and hasattr(client, "models"):
            ids = sorted(m.id for m in client.models.list().data)[:30]
    except Exception:
        pass

    if not ids:
        ids = _FALLBACK_MODELS.get(provider_name, [])

    return [{"id": m, "ready": True} for m in ids]
