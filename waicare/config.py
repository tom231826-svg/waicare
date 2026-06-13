"""Load and validate a WaiCare country configuration.

Everything country-specific lives in one YAML file (see config/fiji.yaml):
locations to watch, the heavy-rain threshold that flags flood risk, the
post-flood high-risk window, languages, emergency contacts and channels.
Adapting WaiCare to a new country means writing a new config file, not new code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml


class ConfigError(ValueError):
    """Raised when a configuration file is missing, malformed or unsafe."""


@dataclass(frozen=True)
class Location:
    name: str
    lat: float
    lon: float
    division: str


@dataclass(frozen=True)
class CountryConfig:
    country: str
    timezone: str
    languages: List[str]
    default_language: str
    emergency: Dict[str, str]
    golden_window_weeks: int  # high-risk weeks after a flood
    heavy_rain_mm: float  # daily precipitation that flags flood risk
    diseases: List[str]
    locations: List[Location]
    channels: List[str]
    past_days: int
    forecast_days: int


def load_config(path) -> CountryConfig:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}")
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path}: invalid YAML: {exc}")
    if not isinstance(raw, dict):
        raise ConfigError(f"{path}: config root must be a mapping")

    for key in ("country", "timezone", "languages", "emergency", "locations"):
        if key not in raw:
            raise ConfigError(f"{path}: missing required key: {key}")

    languages = [str(l) for l in raw["languages"]]
    if not languages:
        raise ConfigError(f"{path}: 'languages' must be a non-empty list")
    default_language = str(raw.get("default_language", languages[0]))
    if default_language not in languages:
        raise ConfigError(f"{path}: default_language {default_language!r} not in languages list")

    emergency = raw["emergency"]
    if not isinstance(emergency, dict) or not emergency:
        raise ConfigError(f"{path}: 'emergency' must be a non-empty mapping")
    emergency = {str(k): str(v) for k, v in emergency.items()}

    heavy_rain_mm = float(raw.get("heavy_rain_mm", 100.0))
    if not 10.0 <= heavy_rain_mm <= 500.0:
        raise ConfigError(f"{path}: heavy_rain_mm {heavy_rain_mm} outside sane range 10-500")

    golden_window_weeks = int(raw.get("golden_window_weeks", 4))
    if not 1 <= golden_window_weeks <= 12:
        raise ConfigError(f"{path}: golden_window_weeks must be between 1 and 12")

    diseases = [str(d) for d in raw.get("diseases", ["leptospirosis", "typhoid", "dengue", "diarrhoea"])]

    past_days = int(raw.get("past_days", 14))
    forecast_days = int(raw.get("forecast_days", 7))
    if not 1 <= past_days <= 92:
        raise ConfigError(f"{path}: past_days must be between 1 and 92")
    if not 1 <= forecast_days <= 16:
        raise ConfigError(f"{path}: forecast_days must be between 1 and 16")

    locations = _parse_locations(raw["locations"], path)
    channels = [str(c) for c in raw.get("channels", ["console"])]

    return CountryConfig(
        country=str(raw["country"]),
        timezone=str(raw["timezone"]),
        languages=languages,
        default_language=default_language,
        emergency=emergency,
        golden_window_weeks=golden_window_weeks,
        heavy_rain_mm=heavy_rain_mm,
        diseases=diseases,
        locations=locations,
        channels=channels,
        past_days=past_days,
        forecast_days=forecast_days,
    )


def _parse_locations(entries, path) -> List[Location]:
    if not isinstance(entries, list) or not entries:
        raise ConfigError(f"{path}: 'locations' must be a non-empty list")
    locations = []
    for item in entries:
        try:
            loc = Location(
                name=str(item["name"]).strip(),
                lat=float(item["lat"]),
                lon=float(item["lon"]),
                division=str(item.get("division", "")).strip(),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(f"{path}: bad location entry {item!r}: {exc}")
        if not loc.name or "|" in loc.name:
            raise ConfigError(f"{path}: location names must be non-empty and contain no '|'")
        if not -90.0 <= loc.lat <= 90.0 or not -180.0 <= loc.lon <= 180.0:
            raise ConfigError(f"{path}: location {loc.name!r} has out-of-range coordinates")
        locations.append(loc)
    return locations
