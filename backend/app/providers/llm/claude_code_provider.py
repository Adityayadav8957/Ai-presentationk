import json
import logging
import os
import subprocess
from collections.abc import Iterator

from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(LLMProvider):
    """Uses a user's own Claude Code subscription instead of separate
    Anthropic API billing, by shelling out to the `claude` CLI in
    non-interactive print mode (`-p`), authenticated via a
    CLAUDE_CODE_OAUTH_TOKEN (generated once, on the user's own machine, via
    `claude setup-token`). Deliberately NOT `--bare` mode — that mode only
    accepts a plain ANTHROPIC_API_KEY, not this token; confirmed directly
    (bare mode replies "Not logged in" even with a valid token set).

    Text-only: Claude Code's headless/`-p` mode does not document image or
    vision input, so multimodal messages are rejected rather than silently
    mishandled — this provider is never used for the vision QA step."""

    def __init__(self, oauth_token: str, model: str | None = None, timeout: int = 180):
        self.oauth_token = oauth_token
        self.model = model
        self.timeout = timeout

    def _flatten_messages(self, messages: list[dict]) -> tuple[str | None, str]:
        system_parts: list[str] = []
        prompt_parts: list[str] = []
        for message in messages:
            content = message.get("content")
            if not isinstance(content, str):
                raise ValueError(
                    "ClaudeCodeProvider only supports plain text messages — Claude Code's "
                    "headless mode does not document image/vision input."
                )
            if message.get("role") == "system":
                system_parts.append(content)
            else:
                prompt_parts.append(content)
        system = "\n\n".join(system_parts) if system_parts else None
        return system, "\n\n".join(prompt_parts)

    def chat(self, messages: list[dict], **kwargs) -> str:
        system, prompt = self._flatten_messages(messages)

        command = ["claude", "-p", prompt, "--output-format", "json"]
        if self.model:
            command += ["--model", self.model]
        if system:
            command += ["--append-system-prompt", system]

        if not self.oauth_token:
            raise RuntimeError(
                "No CLAUDE_CODE_OAUTH_TOKEN configured — run `claude setup-token` on your "
                "own machine and add the result to backend/.env."
            )

        env = {**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": self.oauth_token}

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"claude CLI failed: {exc.stderr.strip()}") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude CLI timed out after {self.timeout}s") from exc
        except FileNotFoundError as exc:
            raise RuntimeError("claude CLI not found — is it installed in this image?") from exc

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.warning("ClaudeCodeProvider: non-JSON output from claude CLI, returning raw stdout")
            return result.stdout.strip()

        text = (payload.get("result") or "").strip()
        if payload.get("is_error"):
            raise RuntimeError(f"claude CLI reported an error: {text or 'unknown error'}")
        return text

    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        # The CLI's headless mode doesn't stream to a script in a way we
        # consume incrementally anywhere in this app — yield the full
        # result once, matching how callers already treat other providers.
        yield self.chat(messages, **kwargs)
