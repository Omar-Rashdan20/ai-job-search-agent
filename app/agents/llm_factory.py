import threading
from typing import Optional

from crewai import LLM

from app.config import (
    LLM_API_BASE,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    OLLAMA_API_BASE,
    OLLAMA_MODEL,
)

_thread_local = threading.local()


def set_llm_provider_override(provider: Optional[str]) -> None:
    _thread_local.provider = provider.strip().lower() if provider else None


def get_active_llm_provider() -> str:
    return getattr(_thread_local, "provider", None) or LLM_PROVIDER


def create_llm(max_tokens: int = 4096) -> LLM:
    provider = get_active_llm_provider()

    if provider == "ollama":
        return LLM(
            model=f"ollama/{OLLAMA_MODEL}",
            api_base=OLLAMA_API_BASE,
            temperature=LLM_TEMPERATURE,
            max_tokens=max_tokens,
        )

    options: dict = dict(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=max_tokens,
    )
    if LLM_API_BASE:
        options["api_base"] = LLM_API_BASE

    return LLM(**options)