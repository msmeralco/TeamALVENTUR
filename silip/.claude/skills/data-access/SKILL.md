---
name: data-access
description: Where SILIP data lives and how to read it - the data/ folders, simulated CSVs, the MQTT topic and payload, the Neon Postgres schema, and the DataSource strategies. Use when writing loaders, queries, ingestion, or anything that reads or stores readings.
---

# Local data (`data/`)
| Folder | What | Git |
|---|---|---|
| `data/raw/` | Real exports (never committed, never read by agents) | ignored |
| `data/sim/` | Output of `make sim` (`silip_ml.readings.simulate`) | ignored, regenerate |
| `data/processed/` | Aggregated tables from `silip_ml.readings.aggregate` | ignored, regenerate |

Simulated CSVs (all rows carry `is_simulated=True`):
- `transformers.csv`: `transformer_id, rated_kva, homes, lat, lon`
- `sin_map.csv`: `sin_hash, transformer_id, has_clamp`
- `transformer_load_15m.csv`: `transformer_id, ts, transformer_kw, load_pct, heat_index_c`
- `outages.csv`: `outage_id, transformer_id, start_ts, cause, duration_min, lat, lon`
- `outage_signals.csv`: `outage_id, kind (last_gasp|report), ts, lat, lon`

# Ingestion
- MQTT topic `silip/v1/{transformer_id}/{sin_hash}/reading`; payload = `silip_ml.readings.domain.Reading` (exported to `schemas/reading.json`).
- AWS IoT Core topic rule forwards to the ingest path; validation happens at the boundary with the Pydantic model.

# Neon (Postgres)
Schema in `db/schema.sql` (additive changes only). Key tables: `transformer`, `household(sin_hash, transformer_id, has_clamp)`, `reading(sin_hash, transformer_id, ts, power_kw, ...)`, `outage`, `outage_signal`. Every table has `is_simulated`.
- Locally the URLs come from `../env/env.dev` (git-ignored): `DATABASE_POOLER_URL` for the app, `DATABASE_DIRECT_URL` for schema changes. In Lambda, from Secrets Manager. Read only in `silip.shared.db`.
- Parameterized queries only. Never select per-household rows into an engineer response.
- TimescaleDB on Neon: [VERIFY] which features are available; the schema works as plain Postgres.

# DataSource strategies (`DATA_SOURCE=`)
- `simulated` (default): reads `data/sim/`. Tests and backtests use this.
- `clamp`: reads `reading` from Neon.
- `smart_meter`: reads smart-meter intervals from Neon (same shape).
All three return the same columns, so services never know which one they got.
