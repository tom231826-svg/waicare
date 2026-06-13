"""Flood-event detection, golden window and the per-event cap."""

from datetime import date

from waicare.config import Location
from waicare.forecast import DailyPrecip
from waicare.trigger import (
    STAGE_ACTIVE,
    STAGE_IMMINENT,
    FloodEvent,
    apply_event_cap,
    collapse_events,
    detect_rain_events,
    prune_state,
    to_windows,
)

BA = Location("Ba", -17.53, 177.67, "Western")


def _precip(pairs):
    return [DailyPrecip(date.fromisoformat(d), mm) for d, mm in pairs]


def test_detect_rain_events_above_threshold():
    dailies = _precip([("2026-06-01", 40), ("2026-06-02", 120), ("2026-06-03", 5)])
    events = detect_rain_events(BA, dailies, heavy_rain_mm=100)
    assert len(events) == 1
    assert events[0].day.isoformat() == "2026-06-02"
    assert events[0].area == "Ba" and events[0].division == "Western"


def test_collapse_keeps_most_recent_past_event():
    events = [
        FloodEvent("Ba", "Western", date(2026, 6, 2), "rain", 120),
        FloodEvent("Ba", "Western", date(2026, 6, 9), "rain", 130),
    ]
    collapsed = collapse_events(events, now=date(2026, 6, 13), weeks=4)
    assert len(collapsed) == 1
    assert collapsed[0].day == date(2026, 6, 9)


def test_collapse_drops_events_outside_window():
    events = [FloodEvent("Ba", "Western", date(2026, 1, 1), "rain", 200)]
    assert collapse_events(events, now=date(2026, 6, 13), weeks=4) == []


def test_to_windows_classifies_active_and_imminent():
    past = [FloodEvent("Ba", "Western", date(2026, 6, 11), "rain", 180)]
    future = [FloodEvent("Nadi", "Western", date(2026, 6, 15), "rain", 150)]
    now = date(2026, 6, 13)
    active = to_windows(past, now, weeks=4)[0]
    imminent = to_windows(future, now, weeks=4)[0]
    assert active.stage == STAGE_ACTIVE and active.days_offset == 2
    assert imminent.stage == STAGE_IMMINENT


def test_to_windows_drops_expired():
    old = [FloodEvent("Ba", "Western", date(2026, 4, 1), "rain", 200)]
    assert to_windows(old, date(2026, 6, 13), weeks=4) == []


def test_event_cap_sends_then_suppresses():
    windows = to_windows([FloodEvent("Ba", "Western", date(2026, 6, 11), "rain", 180)], date(2026, 6, 13), 4)
    to_send, state = apply_event_cap(windows, {})
    assert len(to_send) == 1
    again, _ = apply_event_cap(windows, state)
    assert again == []


def test_event_cap_allows_stage_escalation():
    imminent = to_windows([FloodEvent("Ba", "Western", date(2026, 6, 15), "rain", 180)], date(2026, 6, 13), 4)
    _, state = apply_event_cap(imminent, {})
    active = to_windows([FloodEvent("Ba", "Western", date(2026, 6, 15), "rain", 180)], date(2026, 6, 20), 4)
    to_send, _ = apply_event_cap(active, state)
    assert len(to_send) == 1 and to_send[0].stage == STAGE_ACTIVE


def test_prune_state_drops_old():
    state = {"Ba|2026-01-01|active": "sent", "Ba|2026-06-11|active": "sent"}
    pruned = prune_state(state, date(2026, 6, 13), keep_days=60)
    assert "Ba|2026-06-11|active" in pruned and "Ba|2026-01-01|active" not in pruned
