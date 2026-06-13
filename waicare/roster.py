"""Opt-in subscriber roster loading.

The roster is the ONLY place WaiCare holds contact details, and it lives in a
file you provide (never committed — see .gitignore) to keep deployments in
control of their own data (privacy by design, national data ownership). Each
line is a JSON object:

    {"audience": "general_public", "channel": "whatsapp", "recipient": "+679...",
     "division": "Western", "language": "Fiji Hindi"}

`recipient` is opaque to WaiCare (a phone number, a Viber id, anything the
channel understands). `division` (optional) limits a subscriber to advisories
for their division; `language` (optional) selects the message language. With no
roster file, runs are console/bulletin only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class Subscriber:
    audience: str
    channel: str
    recipient: str
    division: Optional[str] = None
    language: Optional[str] = None


class RosterError(ValueError):
    """Raised when a roster file exists but is malformed."""


def load_roster(path) -> List[Subscriber]:
    path = Path(path)
    if not path.exists():
        return []
    subscribers = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            obj = json.loads(line)
            division = obj.get("division")
            language = obj.get("language")
            sub = Subscriber(
                audience=str(obj["audience"]).strip(),
                channel=str(obj["channel"]).strip(),
                recipient=str(obj["recipient"]).strip(),
                division=str(division).strip() if division else None,
                language=str(language).strip() if language else None,
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise RosterError(f"{path}:{lineno}: invalid roster entry: {exc}")
        if not (sub.audience and sub.channel and sub.recipient):
            raise RosterError(f"{path}:{lineno}: audience, channel and recipient must all be set")
        subscribers.append(sub)
    return subscribers
