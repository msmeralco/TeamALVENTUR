# SILIP spec (v0.3, hackathon prototype)

## Problem
About 196,000 Meralco smart meters serve 8.2 million customers (~3%). Overloads are found after families lose power: in 2024 heat, interruption reports rose from 268 to 732 a day, some restorations took 2 to 3 days. EVs were 24.7% of Jan to Aug 2026 vehicle sales. GEOCC (low-voltage visibility) targets 2030.

## Solution
Opt-in clamps on household wiring (after the meter) → sum by SIN per transformer → forecast and score risk → engineer decides. SILIP sends no SMS or customer notifications.

## Architecture
```
ESP32 clamp node --HTTPS + device key--> API Lambda --> Neon PostgreSQL
smart meters, check meters, SIN map, billing ------^
every 15 min: scoring job --> DB --> sum by SIN --> models (+ weather, EVs, roofs) --> SHAP reasons --> score tables
FastAPI (reads the latest scoring run) --> engineer risk map | outage view | household usage view
```
Scoring runs on a schedule, not on request: [ADR 0002](adr/0002-scheduled-batch-risk-scoring.md).

## Hardware
SCT-013-000 (0 to 100 A, ±1%, 13 mm window, ≤660 V), 22 Ω burden + 10 kΩ/10 kΩ/10 µF bias, 9 V AC-AC voltage ref, ADS1115 or ATM90E32, ESP32, Li-ion for last gasp, labeled enclosure. Licensed electrician installs on the line wire after the meter.

Payload (`POST /api/v1/devices/{device_id}/readings`, header `X-Device-Key` from dashboard registration):
```json
{"ts":"2026-11-12T21:15:00+08:00","voltage_v":219.8,"current_a":11.6,"power_kw":2.43,"power_factor":0.95,"energy_kwh_interval":0.61,"event":null}
```

## Data
Input: clamp readings, smart meter intervals, SIN map, check meters, billing, weather, EV stats, building footprints, outages, reports.
Process: validate → 15-min resample → sum by SIN → join context → models → SHAP.
Output: risk tier + reasons + confidence per transformer, EV/jumper/overload flags, outage pin + ETA range, household usage.

## Models
| Task | Method | Baseline |
| --- | --- | --- |
| Load forecast 24 to 48 h | LightGBM | same hour last week |
| Anomalies | Isolation Forest + residuals | z-score |
| EV / jumper shift | ruptures change points; energy gap | none |
| Risk | rules first, then LightGBM + SHAP | load >100% for 2 h |
| Locate outage | DBSCAN on last gasp + reports | nearest to first report |
| ETA | LightGBM quantile (P10/P50/P90) | median by cause |

## API
Public: `GET /api/v1/outages?status=open`. Engineers: `GET /api/v1/transformers?bbox=` · `GET /api/v1/transformers/{id}` · `GET /api/v1/outages/{id}`. Households: `GET /api/v1/me/usage`. Auth: `docs/auth-contract.md`.

## Rules
RA 7832: never touch the meter, seal, service drop or transformer. RA 10173: opt-in, hashed SINs, transformer totals for Meralco. Decision support only; not a billing device.

## Open questions
ERC rule on customer-side monitors [VERIFY] · which transformers have check meters [VERIFY] · cost of one failure [VERIFY]

## Sources
- powerphilippines.com/?p=25747 (smart meters) · powerphilippines.com/?p=23852 (8.2M customers) · powerphilippines.com/?p=23268 (GEOCC 2030)
- ABS-CBN, 1 May 2024 (268 to 732 reports) · Daily Tribune, 23 Sep 2026 (EVs 24.7%)
- github.com/multica-ai/andrej-karpathy-skills (MIT)
