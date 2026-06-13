"""Opt-in roster loading (with division/language) and state persistence."""

import pytest

from waicare.roster import RosterError, load_roster
from waicare.state import load_state, save_state


def test_missing_roster_is_empty(tmp_path):
    assert load_roster(tmp_path / "none.jsonl") == []


def test_roster_loads_optional_fields(tmp_path):
    path = tmp_path / "roster.jsonl"
    path.write_text(
        '# comment\n'
        '{"audience": "general_public", "channel": "whatsapp", "recipient": "+6799000001", "division": "Western", "language": "Fiji Hindi"}\n'
        '{"audience": "community_health_worker", "channel": "viber", "recipient": "v-1"}\n',
        encoding="utf-8",
    )
    roster = load_roster(path)
    assert len(roster) == 2
    assert roster[0].division == "Western" and roster[0].language == "Fiji Hindi"
    assert roster[1].division is None and roster[1].language is None


def test_roster_rejects_malformed(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"audience": "x", "channel": "viber"}\n', encoding="utf-8")
    with pytest.raises(RosterError):
        load_roster(path)


def test_state_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    save_state(path, {"Ba|2026-06-11|active": "sent"})
    assert load_state(path) == {"Ba|2026-06-11|active": "sent"}


def test_corrupt_state_returns_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{ not json", encoding="utf-8")
    assert load_state(path) == {}
