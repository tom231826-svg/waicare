"""WhatsApp channel — Meta WhatsApp Cloud API (the reference network adapter).

WhatsApp is Jamaica's dominant messaging channel and the Cloud API has a free
tier, which is why it is Heatline's primary delivery path. Credentials come
from the environment, never from code or config (secret management):

  WHATSAPP_TOKEN            Meta Cloud API access token
  WHATSAPP_PHONE_NUMBER_ID  sending phone number id

With no token set the adapter runs in dry-run mode: it logs what *would* be
sent and reports success=dry-run, so the full pipeline is demonstrable without
credentials and CI never makes a network call.
"""

from __future__ import annotations

import os

import requests

from ..compose import OutboundMessage
from .base import DeliveryResult

GRAPH_API_VERSION = "v21.0"
REQUEST_TIMEOUT_S = 30


class WhatsAppChannel:
    name = "whatsapp"

    def __init__(self) -> None:
        self._token = os.environ.get("WHATSAPP_TOKEN", "")
        self._phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")

    @property
    def configured(self) -> bool:
        return bool(self._token and self._phone_number_id)

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        if not self.configured:
            return DeliveryResult(
                self.name, recipient, ok=True,
                detail="dry-run (WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set)",
            )
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{self._phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message.text[:4096]},
        }
        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as exc:  # pragma: no cover - network
            return DeliveryResult(self.name, recipient, ok=False, detail=f"request failed: {exc}")
        if resp.status_code != 200:  # pragma: no cover - network
            return DeliveryResult(
                self.name, recipient, ok=False, detail=f"HTTP {resp.status_code}: {resp.text[:200]}"
            )
        try:  # pragma: no cover - network
            message_id = resp.json()["messages"][0]["id"]
        except (ValueError, KeyError, IndexError):
            message_id = "sent"
        return DeliveryResult(self.name, recipient, ok=True, detail=message_id)  # pragma: no cover
