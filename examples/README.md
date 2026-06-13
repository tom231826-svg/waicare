# Examples

| File | What it is |
|---|---|
| `illustrative_flood.json` | **Illustrative, not live.** A synthetic Open-Meteo precipitation set with a heavy-rain flood in Ba (185 mm, 11 June 2026) to demonstrate the post-flood advisory path on demand. Real captured data: [`../tests/fixtures/fiji_live.json`](../tests/fixtures/fiji_live.json). |
| `sample_bulletin_flood.md` | Bulletin generated from the illustrative flood — shows the full advisory output. |

## Reproduce

```bash
# Illustrative flood scenario (deterministic)
waicare run --fixture examples/illustrative_flood.json \
            --channels console,jsonl --now 2026-06-13T06:00

# Live Fiji precipitation (whatever the weather is today)
waicare run --channels console

# Or declare a flood event manually
waicare run --flood "Ba:Western:2026-06-11:185" --channels console
```
