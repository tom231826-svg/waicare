"""Messenger channel — Meta Graph API Send API.

A second Meta channel sharing the megaphone reach. Same secret-management and
dry-run conventions as the WhatsApp adapter:

  MESSENGER_PAGE_TOKEN  Facebook Page access token
"""

from __future__ import annotations

import os

import requests

from ..compose import OutboundMessage
from .base import DeliveryResult

GRAPH_API_VERSION = "v21.0"
REQUEST_TIMEOUT_S = 30


class MessengerChannel:
    name = "messenger"

    def __init__(self) -> None:
        self._token = os.environ.get("MESSENGER_PAGE_TOKEN", "")

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        if not self.configured:
            return DeliveryResult(
                self.name, recipient, ok=True,
                detail="dry-run (MESSENGER_PAGE_TOKEN not set)",
            )
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/messages"
        payload = {
            "recipient": {"id": recipient},
            "messaging_type": "MESSAGE_TAG",
            "tag": "CONFIRMED_EVENT_UPDATE",
            "message": {"text": message.text[:2000]},
        }
        try:
            resp = requests.post(
                url, json=payload, params={"access_token": self._token}, timeout=REQUEST_TIMEOUT_S
            )
        except requests.RequestException as exc:  # pragma: no cover - network
            return DeliveryResult(self.name, recipient, ok=False, detail=f"request failed: {exc}")
        if resp.status_code != 200:  # pragma: no cover - network
            return DeliveryResult(
                self.name, recipient, ok=False, detail=f"HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return DeliveryResult(self.name, recipient, ok=True, detail="sent")  # pragma: no cover
