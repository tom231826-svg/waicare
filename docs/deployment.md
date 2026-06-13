# Deployment

WaiCare is infrastructure-light: open precipitation data in, advisories out, no
sensors and no database required for a basic deployment.

## 1. Configure

Copy [`config/fiji.yaml`](../config/fiji.yaml) and edit for your country:
`country`, `timezone`, `languages`, `emergency`, `heavy_rain_mm`,
`golden_window_weeks`, `diseases`, `locations` (name/lat/lon/division), `channels`.
**Have the threshold and window reviewed by your health authority.** Then:

```bash
waicare --config config/yourcountry.yaml check
```

## 2. Channels & credentials

Credentials come from the environment. Until set, network channels run in
**dry-run** mode, so the pipeline is fully demonstrable with no accounts.

| Channel | Environment variables |
|---|---|
| `whatsapp` | `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID` (Meta WhatsApp Cloud API) |
| `viber` | `VIBER_AUTH_TOKEN` (Viber public-account / bot) |
| `sms` | `SMS_GATEWAY_URL`, `SMS_FROM`, optional `SMS_AUTH_HEADER` |
| `messenger` | `MESSENGER_PAGE_TOKEN` |
| `console`, `jsonl` | none |

## 3. Subscribers (opt-in)

Create `roster.jsonl` (git-ignored — never commit real contacts) from
[`roster.example.jsonl`](../roster.example.jsonl). Each subscriber has an
audience, channel, recipient, and optional `division` and `language`. The
`community_health_worker` audience is the megaphone: those relayers get briefings
formatted for onward relay and early-symptom referral.

## 4. Run on a schedule

One pass = one `waicare run`. Schedule it (e.g. daily, and after any flood) with
cron:

```cron
0 6 * * *  cd /opt/waicare && ./.venv/bin/waicare run --llm >> run.log 2>&1
```

When a flood is declared officially, you can force an advisory immediately:

```bash
waicare run --flood "Nadi:Western:2026-02-10:210" --llm
```

State in `state.json` carries the per-event cap between runs, so frequent
scheduling will not re-alert the same flood.

## 5. Replicate to another country

New YAML + translated playbooks + local emergency contacts + health-authority
threshold sign-off. No code changes. The same engine powers the Heatline
heat-health warning system — WaiCare is the flood/disease deployment of one
adaptable toolkit.

## Cost

- Open-Meteo: free, no key.
- WhatsApp/Viber: free service tiers.
- AI backend: optional; pennies per run, or run purely on templates.
