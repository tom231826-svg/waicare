# Contributing to WaiCare

Thanks for your interest. WaiCare is an open-source digital public good and
welcomes contributions — especially from people working on flood and climate-
sensitive disease in Fiji, the Pacific, and other LDCs/SIDS.

## Ways to help

- **Country configs & translations.** Add a `config/<country>.yaml` and
  translated `playbooks/`. This is the highest-impact contribution.
- **Channel adapters.** Implement the `Channel` protocol for a new provider.
- **Health review.** If you are a clinician or public-health professional,
  review the LTDD prevention and danger-sign content against best practice and
  national guidance.
- **Bug fixes & tests.**

## Development setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest --cov=waicare      # tests run fully offline (no network, no API keys)
```

## Guidelines

- Keep modules small and single-purpose; only `run.py` should touch network/
  clock/filesystem.
- Add tests for new behaviour. Trigger-logic tests should not depend on the
  network (build precipitation/event fixtures).
- **Health and safety content must stay grounded in cited public-health
  sources** (Fiji MoH, WHO). The symptom advisor must never diagnose or name
  medicines, and must always refer to care. See [docs/safety.md](docs/safety.md).
- Never commit secrets or real subscriber data.

By contributing you agree your contributions are licensed under the
[MIT License](LICENSE).
