"""Precipitation parsing and validation."""

import pytest

from waicare.forecast import ForecastError, parse_daily


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
