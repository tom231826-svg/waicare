"""Precipitation parsing and validation."""

import pytest
import requests

from waicare.forecast import ForecastError, fetch_daily_precip, parse_daily


def test_parse_daily_reads_precip(payload_builder):
    payload = payload_builder("2026-06-01", "2026-06-05", {"2026-06-03": 150.0})
    readings = parse_daily(payload)
    assert len(readings) == 5
    peak = max(readings, key=lambda r: r.precip_mm)
    assert peak.precip_mm == 150.0
    assert peak.day.isoformat() == "2026-06-03"


def test_parse_daily_skips_null_days(payload_builder):
    payload = payload_builder("2026-06-01", "2026-06-03")
    payload["daily"]["precipitation_sum"][1] = None
    assert len(parse_daily(payload)) == 2


def test_parse_daily_missing_block():
    with pytest.raises(ForecastError):
        parse_daily({"hourly": {}})


def test_parse_daily_mismatched_lengths():
    with pytest.raises(ForecastError):
        parse_daily({"daily": {"time": ["2026-06-01"], "precipitation_sum": []}})


def test_parse_daily_all_null():
    with pytest.raises(ForecastError):
        parse_daily({"daily": {"time": ["2026-06-01"], "precipitation_sum": [None]}})


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            exc = requests.HTTPError(f"{self.status_code} error")
            exc.response = self
            raise exc

    def json(self):
        return self.payload


class _FlakySession:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_fetch_daily_precip_retries_timeout(payload_builder):
    payload = payload_builder("2026-06-01", "2026-06-03", {"2026-06-02": 120.0})
    session = _FlakySession(requests.Timeout("slow"), _FakeResponse(payload))
    sleeps = []

    readings = fetch_daily_precip(
        0,
        0,
        past_days=1,
        forecast_days=1,
        timezone="UTC",
        session=session,
        attempts=2,
        backoff_s=0.5,
        sleeper=sleeps.append,
    )

    assert session.calls == 2
    assert sleeps == [0.5]
    assert max(r.precip_mm for r in readings) == 120.0
