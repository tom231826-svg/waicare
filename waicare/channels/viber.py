"""Viber channel — Viber REST bot API.

Viber is, alongside WhatsApp, one of Fiji's common messaging apps, so it is a
first-class channel here. Credentials come from the environment, never code:

  VIBER_AUTH_TOKEN   Viber public-account / bot auth token

With no token set the adapter runs in dry-run mode: it reports success=dry-run
so the full pipeline is demonstrable without credentials and CI never makes a
network call.
"""

from __future__ import annotations

import os

import requests

from ..compose import OutboundMessage
from .base import DeliveryResult

VIBER_SEND_URL = "https://chatapi.viber.com/pa/send_message"
REQUEST_TIMEOUT_S = 30


class ViberChannel:
    name = "viber"

    def __init__(self) -> None:
        self._token = os.environ.get("VIBER_AUTH_TOKEN", "")

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def send(self, recipient: str, message: OutboundMessage) -> DeliveryResult:
        if not self.configured:
            return DeliveryResult(
                self.name, recipient, ok=True, detail="dry-run (VIBER_AUTH_TOKEN not set)"
            )
        payload = {
            "receiver": recipient,
            "type": "text",
            "sender": {"name": "WaiCare"},
            "text": message.text[:7000],
        }
        try:
            resp = requests.post(
                VIBER_SEND_URL,
                json=payload,
                headers={"X-Viber-Auth-Token": self._token},
                timeout=REQUEST_TIMEOUT_S,
            )
        except requests.RequestException as exc:  # pragma: no cover - network
            return DeliveryResult(self.name, recipient, ok=False, detail=f"request failed: {exc}")
        if resp.status_code != 200:  # pragma: no cover - network
            return DeliveryResult(
                self.name, recipient, ok=False, detail=f"HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return DeliveryResult(self.name, recipient, ok=True, detail="sent")  # pragma: no cover
