---
name: data-access
description: Where SILIP data lives and how to read it - the data/ folders, simulated CSVs, the MQTT topic and payload, the Neon Postgres schema, and the DataSource strategies. Use when writing loaders, queries, ingestion, or anything that reads or stores readings.
---

# Local data (`data/`)
| Folder | What | Git |
|---|---|---|
| `data/raw/` | Real exports (never committed, never read by agents) | ignored |
| `data/osm/` | OpenStreetMap transformer sites and nearby building centres (ODbL); `notebooks/00` places transformers and homes here | committed |
| `data/sim/` | Output of `make sim` (`notebooks/00_generate_mock_data.ipynb`, dev scale); `data/sim/large`, `data/sim/xlarge` for timing | ignored, regenerate |
| `tests/fixtures/sim/` | Same notebook at `SIM_SCALE=test` (8 transformers, 21 days, about 2.9 MB) | committed |
| `models/` | Exported models, metadata and parity samples from `notebooks/06` | committed |
| `data/processed/` | Aggregated tables from `silip_ml.readings.aggregate` | ignored, regenerate |

Simulated CSVs (all rows carry `is_simulated=True`; scenario knobs in `data/README.md`):
- `transformers.csv`: `transformer_id, rated_kva, homes, coverage_pct, lat, lon, osm_node_id` (lat/lon are real OSM sites), plus scenario flags `loading_class, ev_site, ev_homes, solar_homes, has_jumper, has_check_meter, lead_up`
- `sin_map.csv`: `sin_hash, transformer_id, has_clamp, lat, lon, osm_way_id` (each home on a real OSM building near its transformer; homes share a building as units when there are too few), plus `has_ev, ev_from, solar_kwp`
- `clamps.csv`: `clamp_id (silip-node-NNNN, the MQTT client ID), sin_hash, ct_model, installed_at, last_seen_at`; one row per `has_clamp` home
- `transformer_load_15m.csv`: `transformer_id, ts, transformer_kw, load_pct, heat_index_c`, plus `measured_kw, homes_reporting, late_readings, duplicate_readings, true_kw, check_meter_kw`. `transformer_kw` is what SILIP sees (clamped homes scaled up); `true_kw` includes jumper load (simulator only, used for trip labels); `check_meter_kw` is blank without a check meter. Intervals with no clamp reporting (outages) are absent.
- `household_load_15m.csv`: per-home kW for a few detail transformers; `readings_raw.csv`: the last 2 days of one transformer as received (`received_at`, late and duplicate arrivals)
- `weather_15m.csv`: `ts, heat_index_c, rain_mm_h, weather (clear|hot_spell|rain|typhoon), is_holiday`
- `weather_forecast_hourly.csv`: `issued_at, ts, cell_id, temperature_c, relative_humidity_pct, precipitation_mm, heat_index_c, kind (archive|forecast)`; archive rows are the observed hour (`issued_at = ts`), forecast rows are issued daily at 00:00 for the next 72 h (truth + error, knob `weather.forecast_error_sd_c`). Cells from `silip_ml.weather.cell_id`; heat index from `silip_ml.weather.heat_index_c` (NOAA). Read only rows with `issued_at` ≤ the scoring time.
- `outages.csv`: `outage_id, transformer_id, start_ts, cause, duration_min, lat, lon`
- `outage_signals.csv`: `outage_id, kind (last_gasp|report), ts, lat, lon`

# Ingestion
- MQTT topic `silip/v1/{transformer_id}/{sin_hash}/reading`; payload = `silip_ml.readings.domain.Reading` (exported to `schemas/reading.json`).
- AWS IoT Core topic rule forwards to the ingest path; validation happens at the boundary with the Pydantic model.

# Neon (Postgres)
Schema in `db/schema.sql` (additive changes only). Key tables: `transformer` (+ `osm_node_id`), `transformer_load`, `household_load`, `household(sin_hash, transformer_id, has_clamp, lat, lon, osm_way_id)`, `clamp(clamp_id, sin_hash UNIQUE, ct_model, installed_at, last_seen_at)`, `reading(sin_hash, transformer_id, ts, power_kw, ...)`, `outage`, `outage_signal`. Every table has `is_simulated`.
- Locally the URLs come from `../env/env.dev` (git-ignored): `DATABASE_POOLER_URL` for the app, `DATABASE_DIRECT_URL` for schema changes. In Lambda, from Secrets Manager. Read only in `silip.shared.db`.
- Parameterized queries only. Never select per-household rows into an engineer response.
- TimescaleDB on Neon: [VERIFY] which features are available; the schema works as plain Postgres.

# DataSource strategies (`DATA_SOURCE=`)
- `simulated` (default): reads `data/sim/`. Tests and backtests use this.
- `neon`: reads `transformer_load` (whole-transformer kW) and `household_load` (per-home kW) plus `transformer`, `outage`, `outage_signal`. Fill it with `uv run python -m silip.shared.load_sim [data/sim]` (idempotent, keeps each row's `is_simulated`; needs `make db` run by the table owner first).
- `clamp`: reads `reading` from Neon.
- `smart_meter`: reads smart-meter intervals from Neon (same shape).
All three return the same columns, so services never know which one they got.
