"""Two-way symptom triage — the half a broadcast cannot do.

A resident asks about symptoms after a flood ("fever and muscle aches since the
flood — what should I watch for?"). WaiCare answers using ONLY the LTDD danger
signs in the reviewed playbooks and the area's current flood status. It is
explicitly constrained to never diagnose, never name medicines, always surface
danger signs, and always direct the person to the nearest health facility — and
to lead with emergency action if the description is severe (do-no-harm).
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from . import llm
from .compose import Playbook, load_prompt
from .config import CountryConfig
from .trigger import AdvisoryWindow

ADVISOR_PROMPT_FILE = "advisor"


def collect_danger_signs(playbooks: List[Playbook]) -> str:
    seen = set()
    signs: List[str] = []
    for playbook in playbooks:
        for sign in playbook.warning_signs:
            key = sign.lower()
            if key not in seen:
                seen.add(key)
                signs.append(sign)
    return "\n".join("- " + s for s in signs)


def area_status_line(window: AdvisoryWindow) -> str:
    if window.stage == "imminent":
        return f"{window.area}: heavy rain expected (~{window.peak_rain_mm:.0f} mm); flooding may be imminent."
    return (
        f"{window.area}: in the post-flood high-risk window "
        f"({window.days_offset} days since heavy rain ~{window.peak_rain_mm:.0f} mm)."
    )


def answer_question(
    question: str,
    area_status: str,
    config: CountryConfig,
    playbooks: List[Playbook],
    language: str,
    prompts_dir="prompts",
) -> str:
    """Answer a symptom question. Requires an LLM backend (raises LLMError if none)."""
    danger_signs = collect_danger_signs(playbooks)
    emergency = next(iter(config.emergency.values()))
    diseases = ", ".join(config.diseases)
    prompt = load_prompt(Path(prompts_dir), ADVISOR_PROMPT_FILE)
    system = prompt.format(
        country=config.country,
        language=language,
        diseases=diseases,
        area_status=area_status,
        danger_signs=danger_signs,
        emergency=emergency,
    )
    return llm.generate(system, question, max_tokens=500)
