"""Channel registry — build the channels named in a country configuration."""

from __future__ import annotations

from typing import Dict, List

from .base import Channel, DeliveryResult
from .console import ConsoleChannel
from .jsonl import JsonlChannel
from .messenger import MessengerChannel
from .sms import SmsChannel
from .viber import ViberChannel
from .whatsapp import WhatsAppChannel

_BUILDERS = {
    "console": ConsoleChannel,
    "jsonl": JsonlChannel,
    "whatsapp": WhatsAppChannel,
    "viber": ViberChannel,
    "messenger": MessengerChannel,
    "sms": SmsChannel,
}


def available_channels() -> List[str]:
    return sorted(_BUILDERS)


def build_channels(names: List[str], jsonl_path: str = "outbox.jsonl") -> Dict[str, Channel]:
    """Instantiate the named channels. Unknown names raise ValueError."""
    unknown = [name for name in names if name not in _BUILDERS]
    if unknown:
        raise ValueError(
            f"unknown channel(s): {', '.join(unknown)}. Available: {', '.join(available_channels())}"
        )
    built: Dict[str, Channel] = {}
    for name in names:
        built[name] = JsonlChannel(jsonl_path) if name == "jsonl" else _BUILDERS[name]()
    return built


__all__ = ["Channel", "DeliveryResult", "build_channels", "available_channels"]
