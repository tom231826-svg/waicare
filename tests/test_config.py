"""Country config loading and validation."""

import pytest

from waicare.config import ConfigError, load_config


def test_load_fiji_config(fiji_config):
    config = load_config(fiji_config)
    assert config.country == "Fiji"
    assert config.timezone == "Pacific/Fiji"
    assert "English" in config.languages and config.default_language == "English"
    assert len(config.locations) == 6
    assert config.golden_window_weeks == 4
    assert config.heavy_rain_mm == 100
    assert {loc.division for loc in config.locations} == {"Western", "Central", "Northern"}


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.yaml")


def _write(tmp_path, body):
    path = tmp_path / "c.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_default_language_must_be_listed(tmp_path):
    body = (
        "country: X\ntimezone: UTC\nlanguages: [English]\ndefault_language: French\n"
        "emergency: {Emergency: '911'}\nlocations:\n  - {name: A, lat: 0, lon: 0}\n"
    )
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, body))


def test_heavy_rain_out_of_range(tmp_path):
    body = (
        "country: X\ntimezone: UTC\nlanguages: [English]\n"
        "emergency: {Emergency: '911'}\nheavy_rain_mm: 5\n"
        "locations:\n  - {name: A, lat: 0, lon: 0}\n"
    )
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, body))


def test_bad_coordinates(tmp_path):
    body = (
        "country: X\ntimezone: UTC\nlanguages: [English]\n"
        "emergency: {Emergency: '911'}\n"
        "locations:\n  - {name: A, lat: 999, lon: 0}\n"
    )
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, body))
