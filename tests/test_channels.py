"""Channel adapters: registry, console, jsonl, and dry-run network channels."""

import json

import pytest

from waicare.channels import available_channels, build_channels
from waicare.channels.viber import ViberChannel
from waicare.compose import OutboundMessage


def _message():
    return OutboundMessage(
        audience="general_public", area="Ba", stage="active", language="English",
        text="Drink only boiled water. Emergency: 911.", voice_script=None, generator="template",
    )


def test_registry_includes_viber():
    assert set(available_channels()) >= {"console", "jsonl", "whatsapp", "viber", "sms", "messenger"}


def test_build_unknown_channel_raises():
    with pytest.raises(ValueError):
        build_channels(["smoke-signal"])


def test_console_channel(capsys):
    build_channels(["console"])["console"].send("general_public@console", _message())
    assert "Ba" in capsys.readouterr().out


def test_jsonl_channel_appends(tmp_path):
    path = tmp_path / "out.jsonl"
    ch = build_channels(["jsonl"], jsonl_path=str(path))["jsonl"]
    ch.send("nurse-1", _message())
    ch.send("nurse-2", _message())
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["recipient"] == "nurse-1"


def test_viber_dry_run_without_token(monkeypatch):
    monkeypatch.delenv("VIBER_AUTH_TOKEN", raising=False)
    channel = ViberChannel()
    assert not channel.configured
    result = channel.send("viber-id", _message())
    assert result.ok and "dry-run" in result.detail


def test_send_never_raises():
    for name in available_channels():
        channel = build_channels([name], jsonl_path="/tmp/waicare_test_outbox.jsonl")[name]
        result = channel.send("recipient", _message())
        assert result.channel == name and isinstance(result.ok, bool)
