"""JSONL channel — appends each message to a newline-delimited JSON file.

This is the megaphone export: community health aides, Red Cross volunteers and
church leaders receive ward-level briefings as a structured file their
coordinators can hand on through their own lists, without Heatline holding any
of those downstream contacts (privacy by design — minimal personal data).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..compose import OutboundMessage
from .base import DeliveryResult


class JsonlChannel:
    name = "jsonl"

    def __init__(self, path: str = "outbox.jsonl") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        record = {
            "recipient": recipient,
            "audience": message.audience,
            "location": message.location,
            "level": message.level,
            "date": message.date,
            "generator": message.generator,
            "text": message.text,
            "voice_script": message.voice_script,
        }
        try:
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            return DeliveryResult(self.name, recipient, ok=False, detail=f"write failed: {exc}")
        return DeliveryResult(self.name, recipient, ok=True, detail=str(self._path))
