"""Message composition, playbook loading and validation."""

from datetime import date

import pytest

from waicare.compose import (
    PlaybookError,
    compose_for_window,
    load_playbooks,
    template_context,
    validate_playbooks,
)
from waicare.config import load_config
from waicare.trigger import AdvisoryWindow


def _window(stage="active"):
    return AdvisoryWindow("Ba", "Western", stage, date(2026, 6, 11), 180.0, 2)


def test_playbooks_load_and_validate(playbooks_dir):
    playbooks = load_playbooks(playbooks_dir)
    assert {p.audience for p in playbooks} >= {
        "general_public", "flood_exposed_workers", "families_with_children", "community_health_worker",
    }
    validate_playbooks(playbooks)


def test_template_context(fiji_config):
    config = load_config(fiji_config)
    ctx = template_context(_window(), config)
    assert ctx["area"] == "Ba" and ctx["division"] == "Western"
    assert ctx["stage"] == "active" and ctx["peak_rain"] == "180"
    assert ctx["emergency"] == "911"


def test_compose_renders_every_audience(playbooks_dir, fiji_config):
    config = load_config(fiji_config)
    playbooks = load_playbooks(playbooks_dir)
    messages = compose_for_window(_window("active"), playbooks, config, use_llm=False)
    assert len(messages) == len(playbooks)
    for message in messages:
        assert "Ba" in message.text
        assert message.generator == "template"
        assert message.language == "English"


def test_compose_imminent_stage(playbooks_dir, fiji_config):
    config = load_config(fiji_config)
    playbooks = load_playbooks(playbooks_dir)
    messages = compose_for_window(_window("imminent"), playbooks, config, use_llm=False)
    assert all(m.stage == "imminent" for m in messages)


def test_voice_script_only_where_configured(playbooks_dir, fiji_config):
    config = load_config(fiji_config)
    by_audience = {m.audience: m for m in compose_for_window(_window(), load_playbooks(playbooks_dir), config)}
    assert by_audience["general_public"].voice_script is not None
    assert by_audience["flood_exposed_workers"].voice_script is None


def test_outbound_message_compat_properties():
    from waicare.compose import OutboundMessage
    msg = OutboundMessage("general_public", "Ba", "active", "English", "text", None, "template")
    assert msg.location == "Ba" and msg.level == "active" and msg.date == ""


def test_validate_detects_bad_placeholder(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "audience: x\ndisplay_name: X\nsources: [s]\nprevention_actions: [a]\n"
        "messages:\n  imminent: 'uses {nope}'\n  active: ok\n",
        encoding="utf-8",
    )
    with pytest.raises(PlaybookError):
        validate_playbooks(load_playbooks(tmp_path))


def test_load_playbooks_empty_dir(tmp_path):
    with pytest.raises(PlaybookError):
        load_playbooks(tmp_path)
