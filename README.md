# WaiCare

**Open-source AI post-flood disease early warning and advisory — built for Fiji, designed for replication across flood-prone Pacific SIDS and other LDCs/SIDS.**

[![CI](https://github.com/tom231826-svg/waicare/actions/workflows/ci.yml/badge.svg)](https://github.com/tom231826-svg/waicare/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

> ⚠️ **Status: working prototype.** WaiCare runs end-to-end today against live
> [Open-Meteo](https://open-meteo.com) precipitation data. It is **not yet
> deployed with a health authority**; its rainfall threshold, high-risk window
> and message content **must be signed off by qualified health professionals
> before any live use.** It is advisory information, not a medical service.

> Part of one adaptable climate-health toolkit with **[Heatline](https://github.com/tom231826-svg/heatline)** (heat-health warning) — same engine, different hazard.

---

## The problem

Every wet season, Fiji faces a predictable second disaster. Floods and cyclones
are followed within weeks by outbreaks of what Fiji's Ministry of Health calls
**LTDD** — **L**eptospirosis, **T**yphoid, **D**engue and **D**iarrhoea —
climate-driven diseases that surge when heavy rain contaminates water and creates
mosquito breeding sites. In early 2025 alone Fiji recorded thousands of dengue
cases and a leptospirosis outbreak with several deaths.

The risk is highest in a **known window** — the two to four weeks after flooding
— yet official prevention reaches people mainly as one-way mass-media broadcasts.
WaiCare turns that predictable window into targeted, two-way protection.

## What it does

```
precipitation / declared flood  →  flood-event detection  →  golden-window (2–4 wk)
   →  audience message (template or multilingual LLM)
   →  WhatsApp / Viber / SMS / bulletin   +   two-way symptom triage
```

1. **Detects** flooding from heavy-rain days (Open-Meteo) or a manually declared
   flood/cyclone event, per town.
2. **Opens a golden window** — the configurable 2–4 week high-risk period after a
   flood — and classifies each area as *imminent* (rain forecast) or *active*.
3. **Composes** plain-language LTDD prevention and early-symptom guidance for each
   audience — the general public, flood-exposed workers (leptospirosis), families
   with young children, and community health workers — and, with AI, **translates
   it across Fiji's three languages** (English, iTaukei Fijian, Fiji Hindi).
4. **Delivers** through WhatsApp, Viber and SMS, and publishes a public bulletin.
5. **Answers** the two-way question a broadcast cannot — *"fever and muscle aches
   since the flood; what should I watch for?"* — pointing to danger signs and the
   nearest health facility, **never diagnosing**.

### Built to be amplified, not stand alone

Warnings work when trusted institutions carry them. WaiCare is built for the
Ministry of Health and community and faith networks to amplify: the
`community_health_worker` playbook is a briefing formatted for onward relay and
early-symptom referral, and delivery is opt-in.

## Quickstart

```bash
git clone https://github.com/tom231826-svg/waicare.git
cd waicare
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Validate the Fiji config and playbooks (no network)
waicare check

# Run against LIVE Fiji precipitation and publish a bulletin
waicare run --channels console

# Simulate a flood event and see the advisory path
waicare run --flood "Ba:Western:2026-06-11:180" --channels console,jsonl --now 2026-06-13T06:00

# See the window a flood opens
waicare activate Ba --division Western --date 2026-06-11 --rain 180 --now 2026-06-13

# Two-way symptom triage (needs an AI key — see "AI backends")
export ANTHROPIC_API_KEY=sk-...
waicare ask --area Ba --days-since 3 "I waded through floodwater and now have fever and sore calves"
```

With no flooding in the data, `waicare run` produces a calm "no areas at risk"
bulletin — the correct, honest output most of the year. Use `--flood` to exercise
the advisory path on demand.

## AI backends (swappable, optional)

WaiCare **never requires** an LLM. With no key it uses static playbook templates
grounded in Fiji MoH and WHO public guidance, so delivery is never blocked. Set
`ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (optionally
`WAICARE_LLM_PROVIDER=anthropic|openai|none` or `WAICARE_LLM_MODEL`) and add
`--llm` to enable AI personalization and translation. Legacy `HEATLINE_LLM_*`
variables are also accepted for shared-toolkit deployments. The model is
constrained to configured source facts, never diagnoses, and falls back to the
template on any error (see [docs/safety.md](docs/safety.md)).

## Adapting to another country

Everything country-specific lives in one file. Copy
[`config/fiji.yaml`](config/fiji.yaml), change the locations, languages,
thresholds and emergency contacts, translate the playbooks, and run. No code
changes. See [docs/deployment.md](docs/deployment.md).

## Documentation

- [Digital Public Goods alignment](docs/DPG-compliance.md)
- [Safety / do-no-harm](docs/safety.md) — thresholds, alert fatigue, the no-diagnosis rule
- [Deployment](docs/deployment.md) — channels, scheduling, replication

## Development

```bash
pip install -e ".[dev]"
pytest --cov=waicare        # fast, fully offline (no network, no API keys)
```

## License & data

Code under the [MIT License](LICENSE). Precipitation data by
[Open-Meteo.com](https://open-meteo.com) (CC-BY 4.0). LTDD guidance grounded in
Fiji Ministry of Health & Medical Services materials and WHO fact sheets on
[leptospirosis](https://www.who.int/health-topics/leptospirosis),
[dengue](https://www.who.int/health-topics/dengue-and-severe-dengue) and
[typhoid](https://www.who.int/health-topics/typhoid).

## Acknowledgements

Built as an entry to the **UNFCCC AI for Climate Action Award (AICA) 2026**, part
of a three-deployment climate-health toolkit with Heatline (heat) and GroundTruth
(loss & damage data).
