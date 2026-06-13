"""Turn a flood advisory window into audience-specific, multilingual messages.

Two modes:
- template: render the reviewed playbook message for the stage. Always available
  — no API key, no network — in the configuration's default language.
- llm: rewrite the template for the audience and, crucially for Fiji, translate
  it into the recipient's language (English, iTaukei Fijian or Fiji Hindi).
  Falls back to the template on any error: personalization is optional,
  delivery is not (do-no-harm).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from . import llm
from .config import CountryConfig
from .trigger import AdvisoryWindow

log = logging.getLogger("waicare.compose")

DEFAULT_PROMPT_FILE = "advisory_message.md"
_CONTEXT_KEYS = ("area", "division", "stage", "peak_rain", "window_weeks", "emergency", "country")


class PlaybookError(ValueError):
    """Raised when playbook content is missing or inconsistent with config."""


@dataclass(frozen=True)
class Playbook:
    audience: str
    display_name: str
    sources: List[str]
    prevention_actions: List[str]
    warning_signs: List[str]
    messages: Dict[str, str]  # stage name -> message template
    voice: bool


@dataclass(frozen=True)
class OutboundMessage:
    audience: str
    area: str
    stage: str
    language: str
    text: str
    voice_script: Optional[str]
    generator: str  # "template" or "llm:<provider>"

    # Compatibility alias so generic channel code can read .location / .level / .date
    @property
    def location(self) -> str:
        return self.area

    @property
    def level(self) -> str:
        return self.stage

    @property
    def date(self) -> str:
        return ""


def load_playbooks(directory) -> List[Playbook]:
    directory = Path(directory)
    files = sorted(directory.glob("*.yaml"))
    if not files:
        raise PlaybookError(f"no playbooks (*.yaml) found in {directory}")
    return [_load_one(path) for path in files]


def _load_one(path: Path) -> Playbook:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PlaybookError(f"{path}: invalid YAML: {exc}")
    if not isinstance(raw, dict):
        raise PlaybookError(f"{path}: playbook root must be a mapping")
    for key in ("audience", "display_name", "sources", "prevention_actions", "messages"):
        if key not in raw:
            raise PlaybookError(f"{path}: missing required key: {key}")
    messages = {str(k).strip().lower(): str(v) for k, v in dict(raw["messages"]).items()}
    return Playbook(
        audience=str(raw["audience"]).strip(),
        display_name=str(raw["display_name"]).strip(),
        sources=[str(s) for s in raw["sources"]],
        prevention_actions=[str(s) for s in raw["prevention_actions"]],
        warning_signs=[str(s) for s in raw.get("warning_signs", [])],
        messages=messages,
        voice=bool(raw.get("voice", False)),
    )


def validate_playbooks(playbooks: List[Playbook], stages=("imminent", "active")) -> None:
    dummy = {key: "x" for key in _CONTEXT_KEYS}
    problems = []
    for playbook in playbooks:
        for stage in stages:
            template = playbook.messages.get(stage)
            if template is None:
                problems.append(f"{playbook.audience}: no message for stage {stage!r}")
                continue
            try:
                template.format(**dummy)
            except (KeyError, IndexError, ValueError) as exc:
                problems.append(f"{playbook.audience}/{stage}: bad template: {exc}")
    if problems:
        raise PlaybookError("playbook validation failed:\n  - " + "\n  - ".join(problems))


def template_context(window: AdvisoryWindow, config: CountryConfig) -> Dict[str, str]:
    return {
        "area": window.area,
        "division": window.division or window.area,
        "stage": window.stage,
        "peak_rain": f"{window.peak_rain_mm:.0f}",
        "window_weeks": str(config.golden_window_weeks),
        "emergency": next(iter(config.emergency.values())),
        "country": config.country,
    }


def compose_one(
    window: AdvisoryWindow,
    playbook: Playbook,
    config: CountryConfig,
    language: str,
    use_llm: bool,
    prompts_dir="prompts",
) -> OutboundMessage:
    context = template_context(window, config)
    base = playbook.messages[window.stage].format(**context).strip()
    text, generator = base, "template"
    if use_llm:
        try:
            text = _llm_rewrite(playbook, window, config, language, Path(prompts_dir), context, base)
            generator = "llm:" + llm.active_provider()
        except llm.LLMError as exc:
            log.warning(
                "LLM personalization failed for %s/%s (%s) — using reviewed template (%s)",
                window.area, playbook.audience, language, exc,
            )
    return OutboundMessage(
        audience=playbook.audience,
        area=window.area,
        stage=window.stage,
        language=language,
        text=text,
        voice_script=_voice_script(text) if playbook.voice else None,
        generator=generator,
    )


def compose_for_window(
    window: AdvisoryWindow,
    playbooks: List[Playbook],
    config: CountryConfig,
    language: Optional[str] = None,
    use_llm: bool = False,
    prompts_dir="prompts",
) -> List[OutboundMessage]:
    lang = language or config.default_language
    return [compose_one(window, pb, config, lang, use_llm, prompts_dir) for pb in playbooks]


def _llm_rewrite(playbook, window, config, language, prompts_dir, context, base) -> str:
    prompt_template = load_prompt(Path(prompts_dir), playbook.audience)
    ctx = dict(context)
    ctx.update(
        {
            "audience": playbook.audience,
            "display_name": playbook.display_name,
            "language": language,
            "prevention_actions": "\n".join("- " + a for a in playbook.prevention_actions),
            "warning_signs": "\n".join("- " + s for s in playbook.warning_signs),
            "base_message": base,
        }
    )
    system = prompt_template.format_map(_SafeDict(ctx))
    return llm.generate(system, "Write the final message now. Output only the message text.")


def load_prompt(prompts_dir: Path, audience: str) -> str:
    prompts_dir = Path(prompts_dir)
    for candidate in (prompts_dir / f"{audience}.md", prompts_dir / DEFAULT_PROMPT_FILE):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise PlaybookError(f"no prompt template found in {prompts_dir} (expected {DEFAULT_PROMPT_FILE})")


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _voice_script(text: str) -> str:
    flat = text.replace("**", "").replace("•", "")
    lines = [line.strip().lstrip("-• ").strip() for line in flat.splitlines()]
    sentences = [line if line.endswith((".", "!", "?", ":")) else line + "." for line in lines if line]
    return " ".join(" ".join(sentences).split())
