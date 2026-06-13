"""Tiny JSON state store for the alert frequency cap.

State is a flat mapping "YYYY-MM-DD|location" -> level already alerted. It holds
no personal data — only which public alerts have already gone out — so it is
safe to commit or to keep on a server (privacy by design).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


def load_state(path) -> Dict[str, str]:
    path = Path(path)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}  # a corrupt state file must not block alerting (do-no-harm)
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def save_state(path, state: Dict[str, str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
