import httpx

from app.core.config import get_settings


def list_pulled_models() -> list[str]:
    settings = get_settings()
    base = settings.ollama_base_url.removesuffix("/v1")
    try:
        response = httpx.get(f"{base}/api/tags", timeout=2)
        response.raise_for_status()
        return [m["name"] for m in response.json().get("models", [])]
    except Exception:
        return []


def ensure_model_pulled(model: str) -> None:
    """Pulls the model if it isn't already present locally. Blocks until the
    pull finishes — callers should report a 'pulling_model' progress step
    first, since this can take a while on first use."""
    settings = get_settings()
    base = settings.ollama_base_url.removesuffix("/v1")

    if model in list_pulled_models():
        return

    with httpx.stream("POST", f"{base}/api/pull", json={"name": model}, timeout=None) as response:
        response.raise_for_status()
        for _ in response.iter_lines():
            pass
