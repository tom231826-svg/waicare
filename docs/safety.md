# Safety / do-no-harm

WaiCare gives health *guidance*, not diagnosis or treatment. Unsafe advice,
over-alerting and false reassurance are treated as design constraints.

## The no-diagnosis rule (symptom triage)

The two-way advisor helps a person decide **whether and how urgently to seek
care** — nothing more. It is constrained (see [`prompts/advisor.md`](../prompts/advisor.md)) to:

- **never diagnose** and **never name or recommend a medicine**;
- **lead with emergency action** ("go to the nearest health centre now", or call
  the emergency number) whenever the description matches a danger sign or
  involves a child, pregnancy, breathing difficulty, bleeding, confusion or
  fainting;
- otherwise give reviewed prevention/self-care steps and advise seeing a health
  centre early, because leptospirosis and typhoid are **treatable when caught
  early**;
- never invent statistics or promise an outcome.

## Alert fatigue

Repeated low-value alerts make people switch off. WaiCare mitigates by design:

- **Event-bounded.** Advisories fire on a flood event and only during the
  configurable golden window — the system does not nag indefinitely.
- **One advisory per event** per area and stage (`trigger.apply_event_cap`); an
  escalation from *imminent* to *active* may send again.

## Thresholds require health-authority sign-off

`heavy_rain_mm` and `golden_window_weeks` in [`config/fiji.yaml`](../config/fiji.yaml)
are starting points informed by Fiji's LTDD experience, **not clinical
thresholds**. They must be reviewed and signed off by the Ministry of Health, and
tuned against local surveillance data, before any live deployment.

## Content grounding

LTDD prevention and danger-sign content is grounded in Fiji Ministry of Health &
Medical Services guidance and WHO fact sheets (leptospirosis, dengue, typhoid,
diarrhoeal disease). Translations are produced by a constrained LLM and should be
reviewed by native speakers before live use.

## Reliability / graceful degradation

- The LLM is **optional**. With no key or on any error, WaiCare uses reviewed
  templates in the default language — it degrades to a dependable broadcast, never
  to silence.
- A corrupt state file is treated as empty rather than blocking advisories.
- `Channel.send` never raises; one bad recipient never aborts the batch.

## Trust

Opt-in only; designed to run on verified Ministry of Health / community accounts
and to be relayed by known community health workers — not as an anonymous bot
messaging strangers.
