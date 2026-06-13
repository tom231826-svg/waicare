"""Swappable AI backends (Anthropic / OpenAI / none) behind one function.

WaiCare never *requires* an LLM. With no key configured, the system falls back
to static playbook templates, so advisory delivery is never blocked by a missing
key or a provider outage (do-no-harm). Set:

  WAICARE_LLM_PROVIDER  anthropic | openai | none   (default: auto-detect)
  WAICARE_LLM_MODEL     model id override
  ANTHROPIC_API_KEY / OPENAI_API_KEY

Legacy HEATLINE_LLM_* variables are accepted as shared-toolkit fallbacks.
"""

from __future__ import annotations

import os

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT_S = 60


class LLMError(RuntimeError):
    """Raised when no provider is usable or a provider call fails."""


def _env(primary: str, fallback: str) -> str:
    return os.environ.get(primary) or os.environ.get(fallback, "")


def active_provider() -> str:
    """Resolve which backend to use: 'anthropic', 'openai' or 'none'."""
    forced = _env("WAICARE_LLM_PROVIDER", "HEATLINE_LLM_PROVIDER").strip().lower()
    if forced == "none":
        return "none"
    if forced == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("WAICARE_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
        return "anthropic"
    if forced == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise LLMError("WAICARE_LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return "openai"
    if forced:
        raise LLMError(f"unknown WAICARE_LLM_PROVIDER {forced!r} (use anthropic, openai or none)")
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    return "none"


def generate(system: str, user: str, max_tokens: int = 700) -> str:
    """One-shot generation with the active provider."""
    provider = active_provider()
    if provider == "none":
        raise LLMError("no LLM provider configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY)")
    if provider == "anthropic":
        return _anthropic(system, user, max_tokens)
    return _openai(system, user, max_tokens)


def _anthropic(system: str, user: str, max_tokens: int) -> str:  # pragma: no cover - network
    model = _env("WAICARE_LLM_MODEL", "HEATLINE_LLM_MODEL") or DEFAULT_ANTHROPIC_MODEL
    resp = requests.post(
        ANTHROPIC_URL,
        timeout=REQUEST_TIMEOUT_S,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
    )
    if resp.status_code != 200:
        raise LLMError(f"Anthropic API error {resp.status_code}: {resp.text[:300]}")
    try:
        data = resp.json()
        text = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
    except (ValueError, KeyError, TypeError) as exc:
        raise LLMError(f"unexpected Anthropic response shape: {exc}") from exc
    if not text.strip():
        raise LLMError("Anthropic returned an empty message")
    return text.strip()


def _openai(system: str, user: str, max_tokens: int) -> str:  # pragma: no cover - network
    model = _env("WAICARE_LLM_MODEL", "HEATLINE_LLM_MODEL") or DEFAULT_OPENAI_MODEL
    resp = requests.post(
        OPENAI_URL,
        timeout=REQUEST_TIMEOUT_S,
        headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]},
        json={
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
    )
    if resp.status_code != 200:
        raise LLMError(f"OpenAI API error {resp.status_code}: {resp.text[:300]}")
    try:
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected OpenAI response shape: {exc}") from exc
    if not text or not text.strip():
        raise LLMError("OpenAI returned an empty message")
    return text.strip()
