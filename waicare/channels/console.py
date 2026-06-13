"""Console channel — prints messages to stdout.

Always available, needs no credentials. This is the default channel for local
runs, CI, and demos, and the reference implementation of the Channel protocol.
"""

from __future__ import annotations

from ..compose import OutboundMessage
from .base import DeliveryResult


class ConsoleChannel:
    name = "console"

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        header = f"[{message.level.upper()}] {message.location} → {message.audience} ({recipient})"
        print(header)
        print("-" * len(header))
        print(message.text)
        if message.voice_script:
            print(f"\n  (voice note script) {message.voice_script}")
        print()
        return DeliveryResult(self.name, recipient, ok=True, detail="printed")
