"""Shared test fixtures and an Open-Meteo daily-precipitation payload builder."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIJI_LOCATIONS = ["Ba", "Nadi", "Lautoka", "Suva", "Nausori", "Labasa"]


@pytest.fixture
def fiji_config() -> Path:
    return REPO_ROOT / "config" / "fiji.yaml"


@pytest.fixture
def playbooks_dir() -> Path:
    return REPO_ROOT / "playbooks"


@pytest.fixture
def prompts_dir() -> Path:
    return REPO_ROOT / "prompts"


def daily_payload(span_start: str, span_end: str, heavy: Dict[str, float] = None) -> dict:
    """Build a synthetic Open-Meteo daily response over an inclusive date span.

    `heavy` maps an ISO date to its precipitation (mm); other days default to a
    light 2 mm. Mirrors the real API's daily block.
    """
    heavy = heavy or {}
    start, end = date.fromisoformat(span_start), date.fromisoformat(span_end)
    times, precip = [], []
    day = start
    while day <= end:
        times.append(day.isoformat())
        precip.append(float(heavy.get(day.isoformat(), 2.0)))
        day += timedelta(days=1)
    return {"daily": {"time": times, "precipitation_sum": precip}}


@pytest.fixture
def payload_builder():
    return daily_payload
