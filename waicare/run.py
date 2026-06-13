"""Orchestrator: one pass of the WaiCare pipeline.

    precipitation (+ manual flood events) → flood-event detection → golden-window
    classification → per-event cap → audience messages (template or multilingual
    LLM) → deliver to channels → write bulletin → save state

Every step is its own module; this file wires them together and is the single
place that touches the network, the clock and the filesystem.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from . import bulletin as bulletin_mod
from .channels import DeliveryResult, build_channels
from .compose import (
    OutboundMessage,
    Playbook,
    compose_for_window,
    compose_one,
    load_playbooks,
    validate_playbooks,
)
from .config import CountryConfig, load_config
from .forecast import fetch_daily_precip, parse_daily
from .roster import Subscriber, load_roster
from .state import load_state, save_state
from .trigger import (
    AdvisoryWindow,
    FloodEvent,
    apply_event_cap,
    collapse_events,
    detect_rain_events,
    prune_state,
    to_windows,
)

log = logging.getLogger("waicare.run")


@dataclass
class RunResult:
    windows: List[AdvisoryWindow]
    sent_windows: List[AdvisoryWindow]
    messages: List[OutboundMessage]
    deliveries: List[DeliveryResult]
    bulletin_path: Optional[Path]

    def summary(self) -> str:
        ok = sum(1 for d in self.deliveries if d.ok)
        return (
            f"{len(self.windows)} area(s) at risk, "
            f"{len(self.sent_windows)} newly advised, "
            f"{len(self.messages)} message(s) composed, "
            f"{ok}/{len(self.deliveries)} deliveries ok"
        )


def run_pipeline(
    config_path,
    now: datetime,
    *,
    fixtures: Optional[Dict[str, dict]] = None,
    extra_events: Optional[List[FloodEvent]] = None,
    use_llm: bool = False,
    channels: Optional[List[str]] = None,
    state_path="state.json",
    bulletin_dir="bulletins",
    roster_path="roster.jsonl",
    outbox_path="bulletins/outbox.jsonl",
    prompts_dir="prompts",
    playbooks_dir="playbooks",
) -> RunResult:
    config = load_config(config_path)
    playbooks = load_playbooks(playbooks_dir)
    validate_playbooks(playbooks)

    channel_names = channels if channels is not None else config.channels
    channel_map = build_channels(channel_names, jsonl_path=outbox_path)
    roster = load_roster(roster_path)

    events = _gather_events(config, fixtures) + list(extra_events or [])
    collapsed = collapse_events(events, now.date(), config.golden_window_weeks)
    all_windows = to_windows(collapsed, now.date(), config.golden_window_weeks)

    state = load_state(state_path)
    to_send, new_state = apply_event_cap(all_windows, state)

    messages: List[OutboundMessage] = []
    for window in to_send:
        messages.extend(
            compose_for_window(window, playbooks, config, use_llm=use_llm, prompts_dir=prompts_dir)
        )

    deliveries = _deliver(to_send, messages, playbooks, channel_map, channel_names, roster, config, use_llm, prompts_dir)
    bulletin_path = bulletin_mod.write_bulletin(bulletin_dir, config, all_windows, messages, now)
    save_state(state_path, prune_state(new_state, now.date()))

    return RunResult(all_windows, to_send, messages, deliveries, bulletin_path)


def _gather_events(config: CountryConfig, fixtures: Optional[Dict[str, dict]]) -> List[FloodEvent]:
    events: List[FloodEvent] = []
    for location in config.locations:
        if fixtures is not None:
            payload = fixtures.get(location.name)
            if payload is None:
                log.warning("no fixture for location %s — skipping", location.name)
                continue
            dailies = parse_daily(payload)
        else:
            dailies = fetch_daily_precip(
                location.lat, location.lon, config.past_days, config.forecast_days, config.timezone
            )
        events.extend(detect_rain_events(location, dailies, config.heavy_rain_mm))
    return events


def _deliver(
    windows: List[AdvisoryWindow],
    broadcast_messages: List[OutboundMessage],
    playbooks: List[Playbook],
    channel_map: Dict[str, object],
    channel_names: List[str],
    roster: List[Subscriber],
    config: CountryConfig,
    use_llm: bool,
    prompts_dir: str,
) -> List[DeliveryResult]:
    results: List[DeliveryResult] = []
    pb_by_audience = {pb.audience: pb for pb in playbooks}
    broadcast = [name for name in channel_names if name in ("console", "jsonl")]

    for message in broadcast_messages:
        for name in broadcast:
            results.append(channel_map[name].send(f"{message.audience}@{name}", message))

    for window in windows:
        for sub in roster:
            if sub.division and window.division and sub.division.lower() != window.division.lower():
                continue
            playbook = pb_by_audience.get(sub.audience)
            if playbook is None:
                continue
            if sub.channel in broadcast:
                continue  # already echoed
            channel = channel_map.get(sub.channel)
            if channel is None:
                results.append(DeliveryResult(sub.channel, sub.recipient, ok=False, detail="channel not enabled"))
                continue
            language = sub.language or config.default_language
            message = compose_one(window, playbook, config, language, use_llm, prompts_dir)
            results.append(channel.send(sub.recipient, message))
    return results


def load_fixture_map(path) -> Dict[str, dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: fixture must map location name -> Open-Meteo payload")
    return data
