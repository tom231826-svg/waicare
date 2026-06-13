"""Open-Meteo precipitation client.

WaiCare watches rainfall, not temperature: heavy rain and flooding are what
precede Fiji's LTDD (leptospirosis, typhoid, dengue, diarrhoea) outbreaks. We
pull daily precipitation totals for recent days (to catch flooding that already
happened and started the high-risk window) and the forecast (to pre-warn).
Open-Meteo is free, needs no API key, and serves any coordinates — which is
what makes WaiCare deployable in any country with a one-file config change.
Weather data by Open-Meteo.com (CC-BY 4.0).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_FIELDS = "precipitation_sum"
REQUEST_TIMEOUT_S = 30


class ForecastError(RuntimeError):
    """Raised when the precipitation provider is unreachable or returns bad data."""


@dataclass(frozen=True)
class DailyPrecip:
    day: date
    precip_mm: float


def fetch_daily_precip(
    lat: float,
    lon: float,
    past_days: int,
    forecast_days: int,
    timezone: str,
    session: Optional[requests.Session] = None,
) -> List[DailyPrecip]:
    """Daily precipitation totals across recent past + forecast days."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_FIELDS,
        "past_days": past_days,
        "forecast_days": forecast_days,
        "timezone": timezone,
    }
    http = session or requests
    try:
        resp = http.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_S)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:  # pragma: no cover - network
        raise ForecastError(f"Open-Meteo request failed for ({lat}, {lon}): {exc}") from exc
    except ValueError as exc:  # pragma: no cover - network
        raise ForecastError(f"Open-Meteo returned non-JSON for ({lat}, {lon})") from exc
    return parse_daily(payload)


def parse_daily(payload: dict) -> List[DailyPrecip]:
    """Validate and convert an Open-Meteo daily response into precip readings."""
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ForecastError("Open-Meteo response is missing the 'daily' block")
    try:
        times = daily["time"]
        precip = daily["precipitation_sum"]
    except KeyError as exc:
        raise ForecastError(f"Open-Meteo response is missing daily field {exc}") from exc
    if len(times) != len(precip):
        raise ForecastError("Open-Meteo daily arrays have mismatched lengths")

    out = []
    for day_str, mm in zip(times, precip):
        if mm is None:
            continue  # provider gap: skip rather than invent a value
        out.append(DailyPrecip(day=date.fromisoformat(day_str), precip_mm=float(mm)))
    if not out:
        raise ForecastError("Open-Meteo returned no usable precipitation readings")
    return out
