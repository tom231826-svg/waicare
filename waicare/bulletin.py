"""Render the public post-flood disease-risk bulletin (markdown).

The bulletin doubles as WaiCare's open record: every run archives which areas
are in the post-flood high-risk window, building a public, dated log of LTDD
risk periods alongside the advisories issued.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .compose import OutboundMessage
from .config import CountryConfig
from .trigger import STAGE_ACTIVE, STAGE_IMMINENT, AdvisoryWindow

REPO_URL = "https://github.com/tom231826-svg/waicare"
BADGES = {STAGE_IMMINENT: "🟠 RAIN INCOMING", STAGE_ACTIVE: "🔴 POST-FLOOD RISK"}


def write_bulletin(directory, config, windows, messages, now) -> Path:
    directory = Path(directory)
    (directory / "archive").mkdir(parents=True, exist_ok=True)
    text = render_bulletin(config, windows, messages, now)
    latest = directory / "latest.md"
    latest.write_text(text, encoding="utf-8")
    (directory / "archive" / f"{now.date().isoformat()}.md").write_text(text, encoding="utf-8")
    return latest


def render_bulletin(
    config: CountryConfig,
    windows: List[AdvisoryWindow],
    messages: List[OutboundMessage],
    now: datetime,
) -> str:
    diseases = ", ".join(config.diseases)
    lines = [
        f"# {config.country} Post-Flood Disease-Risk Bulletin — "
        f"{now.strftime('%A')} {now.day} {now.strftime('%B %Y')}",
        "",
        f"_Generated {now.strftime('%Y-%m-%d %H:%M %Z')} by [WaiCare]({REPO_URL}) from"
        " [Open-Meteo](https://open-meteo.com) precipitation data (CC-BY 4.0)."
        " Advisory information only — not a medical service._",
        "",
        f"Tracking climate-driven disease risk (LTDD: {diseases}) in the"
        f" {config.golden_window_weeks}-week window after heavy rain or flooding.",
        "",
    ]

    if not windows:
        lines += ["**🟢 No areas in a heavy-rain or post-flood high-risk window.**", ""]
    else:
        lines += [
            "## Areas at risk",
            "",
            "| Area | Division | Status | Heavy rain | Timing |",
            "|---|---|---|---|---|",
        ]
        for window in sorted(windows, key=lambda w: (w.stage, w.area)):
            badge = BADGES.get(window.stage, window.stage)
            timing = (
                f"expected {abs(window.days_offset)} day(s) out"
                if window.stage == STAGE_IMMINENT
                else f"{window.days_offset} day(s) since rain"
            )
            lines.append(
                f"| {window.area} | {window.division or '—'} | {badge} |"
                f" {window.peak_rain_mm:.0f} mm | {timing} |"
            )
        lines.append("")

    lines += ["## Advisories issued", ""]
    if messages:
        lines.append(f"_One message per audience for each newly issued advisory (generator: {messages[0].generator})._")
        lines.append("")
        for message in messages:
            quoted = message.text.replace("\n", "\n> ")
            lines += [
                f"**{message.audience}** — {message.area} ({BADGES.get(message.stage, message.stage)})",
                "",
                f"> {quoted}",
                "",
            ]
    else:
        lines += ["_No new advisories this run (no new flood event, or already issued)._", ""]

    emergency = ", ".join(f"{service} {number}" for service, number in config.emergency.items())
    lines += [
        "---",
        "",
        f"**Emergency / health ({config.country}):** {emergency} — or go to the nearest health centre.",
        "",
        "**Grounding sources:** [WHO — Leptospirosis](https://www.who.int/health-topics/leptospirosis) ·"
        " [WHO — Dengue](https://www.who.int/health-topics/dengue-and-severe-dengue) ·"
        " [WHO — Typhoid](https://www.who.int/health-topics/typhoid) ·"
        " Fiji Ministry of Health LTDD guidance",
        "",
    ]
    return "\n".join(lines)
