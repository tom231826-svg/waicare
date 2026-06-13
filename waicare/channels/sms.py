"""SMS channel — generic HTTP gateway adapter.

SMS is the fallback for users without smartphones or data (often the elderly —
the most heat-vulnerable, least-connected group, so this channel matters for
equity, not just completeness). Rather than hard-wire one vendor, this adapter
POSTs to a configurable gateway, so any provider (Twilio, Vonage, a national
aggregator) works by setting environment variables:

  SMS_GATEWAY_URL   endpoint to POST to
  SMS_FROM          sender id / number
  SMS_AUTH_HEADER   value for the Authorization header (optional)

With no gateway URL set the adapter runs in dry-run mode.
"""

from __future__ import annotations

import os

import requests

from ..compose import OutboundMessage
from .base import DeliveryResult

REQUEST_TIMEOUT_S = 30
SMS_SAFE_LENGTH = 480  # ~3 concatenated segments; longer alerts are truncated


class SmsChannel:
    name = "sms"

    def __init__(self) -> None:
        self._url = os.environ.get("SMS_GATEWAY_URL", "")
        self._from = os.environ.get("SMS_FROM", "Heatline")
        self._auth = os.environ.get("SMS_AUTH_HEADER", "")

    @property
    def configured(self) -> bool:
        return bool(self._url)

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        if not self.configured:
            return DeliveryResult(
                self.name, recipient, ok=True, detail="dry-run (SMS_GATEWAY_URL not set)"
            )
        body = _plain_text(message.text)[:SMS_SAFE_LENGTH]
        headers = {"Authorization": self._auth} if self._auth else {}
        try:
            resp = requests.post(
                self._url,
                json={"to": recipient, "from": self._from, "text": body},
                headers=headers,
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as exc:  # pragma: no cover - network
            return DeliveryResult(self.name, recipient, ok=False, detail=f"request failed: {exc}")
        if resp.status_code >= 300:  # pragma: no cover - network
            return DeliveryResult(
                self.name, recipient, ok=False, detail=f"HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return DeliveryResult(self.name, recipient, ok=True, detail="sent")  # pragma: no cover


def _plain_text(text: str) -> str:
    """Strip markdown emphasis so SMS reads cleanly on a basic handset."""
    return text.replace("**", "").replace("•", "-")
