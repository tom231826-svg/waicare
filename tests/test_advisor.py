"""Symptom-triage advisor: helpers (offline) and the no-LLM guard."""

from datetime import date

import pytest

from waicare.advisor import answer_question, area_status_line, collect_danger_signs
from waicare.compose import load_playbooks
from waicare.config import load_config
from waicare.llm import LLMError
from waicare.trigger import AdvisoryWindow


def test_collect_danger_signs(playbooks_dir):
    signs = collect_danger_signs(load_playbooks(playbooks_dir))
    assert "leptospirosis" in signs.lower() or "calf" in signs.lower()


def test_area_status_line_active_vs_imminent():
    active = AdvisoryWindow("Ba", "Western", "active", date(2026, 6, 11), 180.0, 2)
    imminent = AdvisoryWindow("Nadi", "Western", "imminent", date(2026, 6, 15), 150.0, 0)
    assert "high-risk window" in area_status_line(active)
    assert "imminent" in area_status_line(imminent).lower() or "expected" in area_status_line(imminent).lower()


def test_answer_requires_llm(monkeypatch, fiji_config, playbooks_dir):
    monkeypatch.setenv("HEATLINE_LLM_PROVIDER", "none")
    config = load_config(fiji_config)
    playbooks = load_playbooks(playbooks_dir)
    with pytest.raises(LLMError):
        answer_question("fever and sore calves after the flood", "Ba: post-flood window", config, playbooks, "English")
