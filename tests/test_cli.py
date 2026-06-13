"""CLI surface: check / run / activate / ask."""

import json

from waicare.cli import main


def test_check_command(capsys):
    assert main(["check"]) == 0
    assert "Fiji config valid" in capsys.readouterr().out


def test_run_with_manual_flood(tmp_path, capsys):
    code = main([
        "run", "--flood", "Ba:Western:2026-06-11:180", "--channels", "console,jsonl",
        "--state", str(tmp_path / "s.json"), "--bulletins", str(tmp_path / "b"),
        "--roster", str(tmp_path / "r.jsonl"), "--now", "2026-06-13T06:00",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "newly advised" in out
    assert "POST-FLOOD" in (tmp_path / "b" / "latest.md").read_text(encoding="utf-8")


def test_activate_command(capsys):
    code = main(["activate", "Ba", "--division", "Western", "--date", "2026-06-11", "--rain", "180", "--now", "2026-06-13"])
    assert code == 0
    assert "Ba" in capsys.readouterr().out


def test_activate_out_of_window(capsys):
    code = main(["activate", "Ba", "--date", "2026-01-01", "--now", "2026-06-13"])
    assert code == 0
    assert "outside" in capsys.readouterr().out


def test_ask_without_llm_errors(monkeypatch, capsys):
    monkeypatch.setenv("WAICARE_LLM_PROVIDER", "none")
    code = main(["ask", "--area", "Ba", "--days-since", "3", "fever and sore calves"])
    assert code == 2
    assert "error" in capsys.readouterr().err.lower()


def test_bad_config_errors():
    assert main(["--config", "config/nope.yaml", "check"]) == 2
