"""Flood-event detection and the post-flood "golden window".

Unlike a heat warning (a continuous threshold), LTDD risk is event-driven: a
flood or cyclone starts a 2–4 week window in which leptospirosis, typhoid,
dengue and diarrhoea surge. WaiCare therefore:

- detects heavy-rain days from precipitation (a proxy for flooding), and
- accepts manually declared flood events (e.g. an official flood warning),

then, for each affected area, decides whether it is IMMINENT (heavy rain
forecast) or ACTIVE (inside the golden window after rain already fell). Because
an advisory fires per event and the window is time-bounded, the system does not
nag people indefinitely — built-in alert-fatigue mitigation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from .config import CountryConfig, Location
from .forecast import DailyPrecip

STAGE_IMMINENT = "imminent"
STAGE_ACTIVE = "active"


@dataclass(frozen=True)
class FloodEvent:
    area: str
    division: str
    day: date
    source: str  # "rain" (auto) or "manual"
    peak_rain_mm: float


@dataclass(frozen=True)
class AdvisoryWindow:
    area: str
    division: str
    stage: str  # imminent | active
    event_day: date
    peak_rain_mm: float
    days_offset: int  # days until (imminent, negative) or since (active, >=0) the event


def detect_rain_events(location: Location, dailies: List[DailyPrecip], heavy_rain_mm: float) -> List[FloodEvent]:
    """One event per heavy-rain day at a location."""
    events = []
    for reading in dailies:
        if reading.precip_mm >= heavy_rain_mm:
            events.append(
                FloodEvent(
                    area=location.name,
                    division=location.division,
                    day=reading.day,
                    source="rain",
                    peak_rain_mm=round(reading.precip_mm, 1),
                )
            )
    return events


def collapse_events(events: List[FloodEvent], now: date, weeks: int) -> List[FloodEvent]:
    """Keep, per area, the single most relevant recent/upcoming event.

    Drops events older than the golden window or too far in the future, then
    keeps the most recent past event per area (or the soonest upcoming one if no
    past event), so consecutive rainy days don't generate duplicate advisories.
    """
    horizon_past = now - timedelta(weeks=weeks)
    horizon_future = now + timedelta(days=10)
    by_area: Dict[str, FloodEvent] = {}
    for event in events:
        if event.day < horizon_past or event.day > horizon_future:
            continue
        current = by_area.get(event.area)
        if current is None:
            by_area[event.area] = event
            continue
        by_area[event.area] = _prefer(current, event, now)
    return list(by_area.values())


def _prefer(a: FloodEvent, b: FloodEvent, now: date) -> FloodEvent:
    a_past, b_past = a.day <= now, b.day <= now
    if a_past and b_past:
        return a if a.day >= b.day else b  # most recent past
    if a_past != b_past:
        return a if a_past else b  # a past event (in-window) beats a future one
    return a if a.day <= b.day else b  # both future: soonest


def to_windows(events: List[FloodEvent], now: date, weeks: int) -> List[AdvisoryWindow]:
    windows = []
    for event in events:
        offset = (now - event.day).days
        if event.day > now:
            stage = STAGE_IMMINENT
        elif 0 <= offset <= weeks * 7:
            stage = STAGE_ACTIVE
        else:
            continue
        windows.append(
            AdvisoryWindow(
                area=event.area,
                division=event.division,
                stage=stage,
                event_day=event.day,
                peak_rain_mm=event.peak_rain_mm,
                days_offset=offset,
            )
        )
    return windows


def apply_event_cap(
    windows: List[AdvisoryWindow], state: Dict[str, str]
) -> "tuple[List[AdvisoryWindow], Dict[str, str]]":
    """Send one advisory per (area, event week, stage); suppress repeats.

    Keyed by area + ISO event date + stage so the same flood does not re-alert,
    but an escalation from imminent to active does send.
    """
    new_state = dict(state)
    to_send = []
    for window in windows:
        key = f"{window.area}|{window.event_day.isoformat()}|{window.stage}"
        if key in new_state:
            continue
        to_send.append(window)
        new_state[key] = "sent"
    return to_send, new_state


def prune_state(state: Dict[str, str], today: date, keep_days: int = 120) -> Dict[str, str]:
    cutoff = today - timedelta(days=keep_days)
    pruned = {}
    for key, value in state.items():
        parts = key.split("|")
        if len(parts) < 2:
            continue
        try:
            event_day = date.fromisoformat(parts[1])
        except ValueError:
            continue
        if event_day >= cutoff:
            pruned[key] = value
    return pruned
