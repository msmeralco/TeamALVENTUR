# data

Nothing here is committed except this file and `osm/`. Everything else can be regenerated.

- `raw/`: real exports (smart meters, check meters, outages). Never committed, never read by agents. SINs only as `sin_hash`.
- `osm/`: committed OpenStreetMap snapshot of real transformer sites and building centres (ODbL 1.0); see `osm/README.md`.
- `sim/`: output of `make sim`, which executes `notebooks/00_generate_mock_data.ipynb` (dev scale, seed 7). Every row has `is_simulated=True`. `sim/large/` and `sim/xlarge/` are timing-only sets (`make sim SIM_SCALE=large`).
- `processed/`: aggregated tables built from `raw/` or `sim/` by `silip_ml.readings.aggregate`.

## Mock data scenarios

`notebooks/00_generate_mock_data.ipynb` is the only generator. Each scenario is a named knob in its `SCENARIOS` cell, seeded by `SIM_SEED` (default 7). `[VERIFY]` marks placeholders nobody has checked against a real source.

| Scenario | Knob (`SCENARIOS[...]`) | Value | Source |
|---|---|---|---|
| Scale | `SIM_SCALE` env: `test`, `dev`, `large`, `xlarge` | 8×21 d, 50×56 d, 2,000×14 d, 4,000×14 d (transformers × days) | design choice |
| Holidays, weekends | `calendar.holidays`, `home_daytime_extra_kw` | Holy Week, Araw ng Kagitingan, Labor Day, Independence Day 2026; +0.25 kW daytime at home | `[VERIFY]` 2026 proclamation; extra kW `[VERIFY]` |
| Heat | `weather.daily_max_heat_index_c`, `day_night_swing_c` | mean 39 °C, spread 1.5, 7 °C day-night swing | `[VERIFY]` PAGASA |
| Hot spells | `weather.hot_spells_per_30_days`, `hot_spell_days`, `hot_spell_extra_c` | 1.5 per 30 days, 3 to 5 days, +4 °C | `[VERIFY]` |
| Rain, typhoon | `weather.rain_day_share`, `typhoon_days_after_day_40`, cooling | 6% of days, 1 typhoon after day 40; −5 / −8 °C | `[VERIFY]` |
| Aircon | `aircon.kw_per_home`, heat scale | 0.8 to 1.6 kW × clip((HI − 30)/10, 0, 1.5) | silip-domain skill |
| EV adoption | `ev.site_share`, `home_share_by_end`, `charger_kw` | 20% of transformers; 15% of homes there by the end, 1% elsewhere; 3.3 to 7.4 kW from 8 PM | charger and 8 PM: silip-domain; EVs 24.7% of Jan to Aug 2026 sales (SPEC#sources) as context; shares `[VERIFY]` |
| Rooftop solar | `solar.home_share`, `kwp` | 5% of homes, 2 to 4 kWp | `[VERIFY]` |
| Jumpers, check meters | `jumpers.transformer_share`, `kw`, `check_meter_share` | 10% of transformers, 2 to 8 kW evening-heavy; 30% have a check meter | `[VERIFY]`; SPEC open question |
| Clamp reality | `clamps.coverage`, `installed_during_run_share`, `offline_share`, `wifi_drops_per_day`, `missing_interval_share`, `late_share`, `duplicate_share`, `noise_share` | 30 to 90% opt-in; 20% installed mid-run; 5% die; 0.03 Wi-Fi drops a day of 1 to 12 h; 1% missing; 2% late; 0.5% duplicated; ±1% noise | noise: SCT-013-000 ±1% (SPEC#hardware); rest `[VERIFY]` |
| Transformer mix | `transformers.ratings_kva`, `homes`, `base_kw`, `loading_mix` | 25 to 100 kVA, 20 to 60 homes, 0.2 to 0.6 kW base; light 30%, normal 45%, tight 15%, over 10% | ratings, homes, base: silip-domain; mix `[VERIFY]` |
| Failures with a lead-up | `transformers.lead_up_share`, `lead_up_growth`, `lead_up_days` | 10% of non-light transformers grow 10 to 20% over the last 7 to 12 days | `[VERIFY]` |
| Outages | `outages.other_per_day`, `rain_multiplier`, `typhoon_multiplier`, `median_minutes` | 0.05 a day; ×3 rain, ×15 typhoon; medians 180 / 150 / 240 min | trip rule and medians: silip-domain; multipliers `[VERIFY]` |

Kept from the old simulator: OSM transformer sites and building-placed households (read directly from `data/osm/*.csv`), `clamps.csv`, outages and their signals, and the same file names and columns (new columns are added at the end).
