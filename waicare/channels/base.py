"""Channel adapter protocol — the contract every delivery channel implements.

Platform independence (a Digital Public Goods Standard requirement) is realised
here: the rest of Heatline produces OutboundMessage objects and never knows
which channel carries them. Adding a channel means implementing one method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..compose import OutboundMessage


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    recipient: str
    ok: bool
    detail: str  # provider message id on success, or the error/dry-run reason


@runtime_checkable
class Channel(Protocol):
    name: str

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        """Deliver one message to one recipient. Must never raise: a failed
        send returns DeliveryResult(ok=False, ...) so one bad recipient never
        blocks the rest of the batch (do-no-harm)."""
        ...
