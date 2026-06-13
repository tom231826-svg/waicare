# Digital Public Goods Standard — self-assessment

WaiCare is designed against the [Digital Public Goods Standard](https://digitalpublicgoods.net/standard/)
(9 indicators). This is a self-assessment of the prototype; formal DPG registry
recognition will be pursued separately.

| # | Indicator | Status | Evidence |
|---|---|---|---|
| 1 | **Relevance to SDGs** | ✅ | SDG 3 (health), 13 (climate action). Reduces post-flood LTDD illness via timely prevention. |
| 2 | **Open licence** | ✅ | [MIT](../LICENSE) for code; precipitation data Open-Meteo CC-BY 4.0; bulletins CC-BY. |
| 3 | **Clear ownership** | ✅ | Copyright held by WaiCare contributors; licence makes ownership explicit. |
| 4 | **Platform independence** | ✅ | No mandatory proprietary dependency. Channels are swappable adapters (`channels/` — WhatsApp, Viber, SMS, …); the AI backend is swappable and **optional** (`llm.py`); shares its engine with Heatline. |
| 5 | **Documentation** | ✅ | [README](../README.md), this doc, [safety](safety.md), [deployment](deployment.md), inline module docs, offline test suite. |
| 6 | **Non-PII data / export mechanism** | ✅ | Bulletins are reproducible from open inputs; subscriber data is never embedded. |
| 7 | **Privacy & applicable laws** | ✅ | Opt-in only; minimal data; contacts kept out of the repo and under the deploying authority's control. See [safety.md](safety.md). |
| 8 | **Standards & best practices** | ✅ | Grounded in Fiji MoH LTDD guidance + WHO fact sheets; conventional Python packaging; CI on Python 3.9/3.11/3.12. |
| 9 | **Do no harm by design** | ✅ | Event-bounded advisories (no indefinite nagging), per-event cap, **symptom triage that never diagnoses and always refers to care**, human-reviewed content, LLM constrained + template fallback. See [safety.md](safety.md). |

## What is not yet done

- Formal submission to the DPG registry.
- Independent clinical review of the LTDD content (currently grounded in Fiji
  MoH + WHO public guidance; sign-off required before live use).
- A deployment partnership with the Fiji Ministry of Health.
