"""LLM provider resolution and the do-no-harm template fallback."""

from datetime import date

import pytest

from waicare import llm
from waicare.compose import compose_for_window, load_playbooks
from waicare.config import load_config
from waicare.trigger import AdvisoryWindow


def test_active_provider_none(monkeypatch):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    assert llm.active_provider() == "none"


def test_active_provider_autodetect(monkeypatch):
    monkeypatch.delenv("HEATLINE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert llm.active_provider() == "anthropic"


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "wizard")
    with pytest.raises(llm.LLMError):
        llm.active_provider()


def test_compose_falls_back_to_template_without_llm(monkeypatch, fiji_config, playbooks_dir):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    config = load_config(fiji_config)
    playbooks = load_playbooks(playbooks_dir)
    window = AdvisoryWindow("Ba", "Western", "active", date(2026, 6, 11), 180.0, 2)
    messages = compose_for_window(window, playbooks, config, language="Fiji Hindi", use_llm=True)
    # No backend → falls back to reviewed English template, delivery still happens.
    assert all(m.generator == "template" for m in messages)
    assert all("Ba" in m.text for m in messages)
