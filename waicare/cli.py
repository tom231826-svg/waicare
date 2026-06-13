"""Command-line interface: `waicare check | run | activate | ask`."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional

from . import llm
from .advisor import answer_question, area_status_line
from .channels import available_channels
from .compose import load_playbooks, validate_playbooks
from .config import ConfigError, load_config
from .forecast import ForecastError
from .run import load_fixture_map, run_pipeline
from .trigger import FloodEvent, collapse_events, to_windows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="waicare", description="Post-flood disease (LTDD) early warning and advisory.")
    parser.add_argument("--config", default="config/fiji.yaml", help="country config file")
    parser.add_argument("--playbooks", default="playbooks", help="playbooks directory")
    parser.add_argument("--prompts", default="prompts", help="prompt templates directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run one advisory pipeline pass")
    run.add_argument("--fixture", help="offline Open-Meteo precip fixture JSON (no network)")
    run.add_argument("--llm", action="store_true", help="personalise/translate messages with an LLM backend")
    run.add_argument("--channels", help=f"comma-separated; available: {', '.join(available_channels())}")
    run.add_argument("--state", default="state.json")
    run.add_argument("--bulletins", default="bulletins")
    run.add_argument("--roster", default="roster.jsonl")
    run.add_argument("--now", help="override current time (ISO 8601), for testing/replay")
    run.add_argument("--flood", action="append", default=[],
                     help="manual flood event AREA:DIVISION:YYYY-MM-DD[:mm], repeatable")

    act = sub.add_parser("activate", help="show the advisory window a manual flood event would open")
    act.add_argument("area")
    act.add_argument("--division", default="")
    act.add_argument("--date", required=True, help="flood date YYYY-MM-DD")
    act.add_argument("--rain", type=float, default=0.0, help="reported rainfall mm")
    act.add_argument("--now")

    ask = sub.add_parser("ask", help="answer a resident's symptom question (needs LLM backend)")
    ask.add_argument("--area", required=True)
    ask.add_argument("--language")
    ask.add_argument("--days-since", type=int, default=2, help="days since the flood")
    ask.add_argument("--rain", type=float, default=120.0)
    ask.add_argument("question")

    sub.add_parser("check", help="validate config and playbooks, no network")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        if args.command == "check":
            return _cmd_check(args)
        if args.command == "run":
            return _cmd_run(args)
        if args.command == "activate":
            return _cmd_activate(args)
        if args.command == "ask":
            return _cmd_ask(args)
    except (ConfigError, ForecastError, llm.LLMError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1


def _now_from(value: Optional[str]) -> datetime:
    return datetime.fromisoformat(value) if value else datetime.now()


def _parse_flood(spec: str) -> FloodEvent:
    parts = spec.split(":")
    if len(parts) < 3:
        raise ValueError(f"--flood expects AREA:DIVISION:YYYY-MM-DD[:mm], got {spec!r}")
    area, division, day_str = parts[0], parts[1], parts[2]
    rain = float(parts[3]) if len(parts) > 3 and parts[3] else 0.0
    return FloodEvent(area=area, division=division, day=date.fromisoformat(day_str), source="manual", peak_rain_mm=rain)


def _cmd_check(args) -> int:
    config = load_config(args.config)
    playbooks = load_playbooks(args.playbooks)
    validate_playbooks(playbooks)
    print(f"OK: {config.country} config valid — {len(config.locations)} location(s), "
          f"{len(playbooks)} playbook(s), {config.golden_window_weeks}-week window.")
    print(f"     languages: {', '.join(config.languages)} | channels: {', '.join(config.channels)} | "
          f"LLM backend: {llm.active_provider()}")
    return 0


def _cmd_run(args) -> int:
    fixtures = load_fixture_map(args.fixture) if args.fixture else None
    channels = [c.strip() for c in args.channels.split(",")] if args.channels else None
    extra_events = [_parse_flood(spec) for spec in args.flood]
    result = run_pipeline(
        args.config,
        _now_from(args.now),
        fixtures=fixtures,
        extra_events=extra_events,
        use_llm=args.llm,
        channels=channels,
        state_path=args.state,
        bulletin_dir=args.bulletins,
        roster_path=args.roster,
        outbox_path=str(Path(args.bulletins) / "outbox.jsonl"),
        prompts_dir=args.prompts,
        playbooks_dir=args.playbooks,
    )
    print(result.summary())
    if result.bulletin_path:
        print(f"bulletin: {result.bulletin_path}")
    return 0


def _cmd_activate(args) -> int:
    config = load_config(args.config)
    now = _now_from(args.now)
    event = FloodEvent(args.area, args.division, date.fromisoformat(args.date), "manual", args.rain)
    windows = to_windows(collapse_events([event], now.date(), config.golden_window_weeks), now.date(), config.golden_window_weeks)
    if not windows:
        print(f"{args.area}: that flood date is outside the {config.golden_window_weeks}-week window from {now.date()}.")
        return 0
    for window in windows:
        print(area_status_line(window))
    return 0


def _cmd_ask(args) -> int:
    config = load_config(args.config)
    playbooks = load_playbooks(args.playbooks)
    from .trigger import AdvisoryWindow
    stage = "imminent" if args.days_since < 0 else "active"
    window = AdvisoryWindow(args.area, "", stage, date.fromisoformat("2025-01-01"), args.rain, max(0, args.days_since))
    status = area_status_line(window)
    language = args.language or config.default_language
    answer = answer_question(args.question, status, config, playbooks, language, prompts_dir=args.prompts)
    print(answer)
    return 0
