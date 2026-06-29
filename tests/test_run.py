"""End-to-end pipeline run, offline via fixtures (no network, no LLM)."""

from datetime import datetime

import pytest

from waicare.forecast import ForecastError, parse_daily
from waicare.run import run_pipeline

NOW = datetime(2026, 6, 13, 6, 0)
LOCATIONS = ["Ba", "Nadi", "Lautoka", "Suva", "Nausori", "Labasa"]
SPAN = ("2026-05-16", "2026-06-20")


@pytest.fixture
def fixtures(payload_builder):
    """Ba had a heavy-rain flood two days before NOW; everywhere else is dry."""
    out = {}
    for name in LOCATIONS:
        heavy = {"2026-06-11": 180.0} if name == "Ba" else {}
        out[name] = payload_builder(SPAN[0], SPAN[1], heavy)
    return out


def _run(tmp_path, fixtures, **kw):
    return run_pipeline(
        "config/fiji.yaml",
        NOW,
        fixtures=fixtures,
        state_path=str(tmp_path / "state.json"),
        bulletin_dir=str(tmp_path / "bulletins"),
        roster_path=str(tmp_path / "roster.jsonl"),
        outbox_path=str(tmp_path / "bulletins" / "outbox.jsonl"),
        **kw,
    )


def _live_run(tmp_path, **kw):
    return run_pipeline(
        "config/fiji.yaml",
        NOW,
        state_path=str(tmp_path / "state.json"),
        bulletin_dir=str(tmp_path / "bulletins"),
        roster_path=str(tmp_path / "roster.jsonl"),
        outbox_path=str(tmp_path / "bulletins" / "outbox.jsonl"),
        **kw,
    )


def test_pipeline_detects_active_window(tmp_path, fixtures):
    result = _run(tmp_path, fixtures)
    assert any(w.area == "Ba" and w.stage == "active" for w in result.windows)
    assert len(result.sent_windows) == 1
    assert len(result.messages) == 4  # one per playbook audience
    assert result.messages and all(d.ok for d in result.deliveries)


def test_pipeline_writes_bulletin(tmp_path, fixtures):
    result = _run(tmp_path, fixtures)
    text = result.bulletin_path.read_text(encoding="utf-8")
    assert "Ba" in text and "POST-FLOOD" in text
    assert (tmp_path / "bulletins" / "archive" / "2026-06-13.md").exists()


def test_event_cap_suppresses_second_run(tmp_path, fixtures):
    assert len(_run(tmp_path, fixtures).messages) == 4
    second = _run(tmp_path, fixtures)
    assert second.messages == [] and second.sent_windows == []
    assert any(w.area == "Ba" for w in second.windows)  # still shown in outlook


def test_manual_flood_event(tmp_path, payload_builder):
    dry = {name: payload_builder(SPAN[0], SPAN[1], {}) for name in LOCATIONS}
    from waicare.trigger import FloodEvent
    from datetime import date
    event = FloodEvent("Nadi", "Western", date(2026, 6, 12), "manual", 200.0)
    result = _run(tmp_path, dry, extra_events=[event])
    assert any(w.area == "Nadi" and w.stage == "active" for w in result.sent_windows)


def test_calm_everywhere_sends_nothing(tmp_path, payload_builder):
    dry = {name: payload_builder(SPAN[0], SPAN[1], {}) for name in LOCATIONS}
    result = _run(tmp_path, dry)
    assert result.windows == [] and result.messages == []
    assert result.bulletin_path.exists()


def test_roster_delivery_to_division(tmp_path, fixtures):
    roster = tmp_path / "roster.jsonl"
    roster.write_text(
        '{"audience": "general_public", "channel": "whatsapp", "recipient": "+6799000001", "division": "Western"}\n'
        '{"audience": "general_public", "channel": "whatsapp", "recipient": "+6799000999", "division": "Northern"}\n',
        encoding="utf-8",
    )
    result = run_pipeline(
        "config/fiji.yaml", NOW, fixtures=fixtures,
        state_path=str(tmp_path / "s.json"), bulletin_dir=str(tmp_path / "b"),
        roster_path=str(roster), outbox_path=str(tmp_path / "b" / "outbox.jsonl"),
        channels=["console", "whatsapp"],
    )
    # Ba is in Western, so only the Western subscriber should get a targeted send.
    whatsapp = [d for d in result.deliveries if d.channel == "whatsapp"]
    assert len(whatsapp) == 1 and whatsapp[0].recipient == "+6799000001"


def test_live_pipeline_skips_one_forecast_failure(tmp_path, payload_builder, monkeypatch, caplog):
    def fake_fetch(lat, lon, past_days, forecast_days, timezone):
        if round(lat, 2) == -17.61:  # Lautoka timed out in the observed Actions failure.
            raise ForecastError("timeout")
        heavy = {"2026-06-11": 180.0} if round(lat, 2) == -17.53 else {}
        return parse_daily(payload_builder(SPAN[0], SPAN[1], heavy))

    monkeypatch.setattr("waicare.run.fetch_daily_precip", fake_fetch)
    caplog.set_level("WARNING", logger="waicare.run")

    result = _live_run(tmp_path)

    assert any(w.area == "Ba" and w.stage == "active" for w in result.windows)
    assert len(result.messages) == 4
    assert "weather unavailable for Lautoka" in caplog.text


def test_live_pipeline_fails_when_all_forecasts_fail(tmp_path, monkeypatch):
    def fake_fetch(lat, lon, past_days, forecast_days, timezone):
        raise ForecastError("timeout")

    monkeypatch.setattr("waicare.run.fetch_daily_precip", fake_fetch)

    with pytest.raises(ForecastError, match="Open-Meteo failed for all 6 location"):
        _live_run(tmp_path)
