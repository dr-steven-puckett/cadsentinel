from __future__ import annotations

from typing import Literal

from app.config import get_settings

SecurityMode = Literal["secure", "not_secure"]

_settings = get_settings()

# Initialize mode from settings/chat provider:
# if chat provider is ollama → start in "secure"; else "not_secure"
_mode: SecurityMode = (
    "secure" if (_settings.chat_provider_name or "").lower() == "ollama" else "not_secure"
)


def get_security_mode() -> SecurityMode:
    """
    Return the current global security mode.

    - "secure"     → local-only providers (Ollama)
    - "not_secure" → cloud/OpenAI providers
    """
    return _mode


def set_security_mode(mode: SecurityMode) -> SecurityMode:
    """
    Set the global security mode at runtime.
    """
    global _mode
    if mode not in ("secure", "not_secure"):
        raise ValueError(f"Invalid security mode: {mode!r}")
    _mode = mode
    return _mode


def get_effective_providers() -> dict[str, str]:
    """
    Map current security mode to concrete provider names.

    This is where we encode the rule:
      - "secure"     → "ollama"
      - "not_secure" → "openai"
    """
    mode = get_security_mode()
    if mode == "secure":
        return {"chat": "ollama", "embedding": "ollama"}
    else:
        return {"chat": "openai", "embedding": "openai"}
