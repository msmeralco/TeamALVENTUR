# data

Nothing here is committed except this file and `osm/`. Everything else can be regenerated.

- `raw/`: real exports (smart meters, check meters, outages). Never committed, never read by agents. SINs only as `sin_hash`.
- `osm/`: committed OpenStreetMap snapshot of real transformer sites and building centres (ODbL 1.0); see `osm/README.md`.
- `sim/`: output of `make sim`, which executes `notebooks/00_generate_mock_data.ipynb` (dev scale, seed 7). Every row has `is_simulated=True`; dev also adds temporary simulated T-Meralco transformer totals and a simulated `silip-esp32-test` map point at the registered coordinates. They are fixture rows; live Neon registrations and readings remain separate. `sim/large/` and `sim/xlarge/` are timing-only sets (`make sim SIM_SCALE=large`).
- `processed/`: aggregated tables built from `raw/` or `sim/` by `silip_ml.readings.aggregate`.

## Mock data scenarios

`notebooks/00_generate_mock_data.ipynb` is the only generator. Each scenario is a named knob in its `SCENARIOS` cell, seeded by `SIM_SEED` (default 7). `[VERIFY]` marks placeholders nobody has checked against a real source.

| Scenario | Knob (`SCENARIOS[...]`) | Value | Source |
|---|---|---|---|
| Scale | `SIM_SCALE` env: `test`, `dev`, `large`, `xlarge` | 8×21 d, 50×56 d plus one dev-only T-Meralco anchor, 2,000×14 d, 4,000×14 d (transformers × days) | design choice |
| Holidays, weekends | `calendar.holidays`, `home_daytime_extra_kw` | Holy Week, Araw ng Kagitingan, Labor Day, Independence Day 2026; +0.25 kW daytime at home | `[VERIFY]` 2026 proclamation; extra kW `[VERIFY]` |
| Heat | `weather.daily_max_heat_index_c`, `day_night_swing_c` | mean 39 °C, spread 1.5, 7 °C day-night swing | `[VERIFY]` PAGASA |
| Hot spells | `weather.hot_spells_per_30_days`, `hot_spell_days`, `hot_spell_extra_c` | 1.5 per 30 days, 3 to 5 days, +4 °C | `[VERIFY]` |
| Humidity, hourly weather | `weather.humidity_pct`, `wet_humidity_extra_pct` | 85% at 2 AM to 60% at 2 PM, +10 points on rain and typhoon days, ±3 noise; temperature is solved so the NOAA heat index (`silip_ml.weather.heat_index_c`) matches the simulator's within 0.05 °C (humidity is lowered a little where NOAA's formula jumps near 27 °C) | `[VERIFY]` PAGASA |
| Day-ahead forecast error | `weather.forecast_error_sd_c`, `forecast_error_growth_per_day`, `forecast_error_sd_rh_pct`, `forecast_rain_error_sigma` | temperature error sd 0.7 °C per issue and lead day, ×(1 + 0.1 × lead day), plus hourly jitter of sd/3; humidity holds the true dew point (Magnus formula, `notebooks/_weather.py`), so a warm forecast is drier, plus humidity sd 0 points per lead day; rain × lognormal(0, 0.5). Daily-max heat index MAE at lead day 0: 0.78 °C (dev, seed 7), 0.75 (seed 8), 0.83 (test); hourly heat index MAE about 1.0 / 1.0 / 1.1 °C on lead days 0 / 1 / 2 (dev). `notebooks/00` asserts 0.6 to 1.0 °C at dev scale, `tests/ml/test_weather.py` on the fixtures | temperature, humidity and growth: calibrated to measured Open-Meteo day-ahead skill vs ERA5 for Metro Manila, 2025-11..2026-10, `notebooks/weather_skill.py` (`notebooks/results/weather_skill.json`: daily-max heat index MAE 0.79 °C, 0.69 in March to May; temperature and humidity errors anti-correlated −0.91 to −0.96). Forecast vs reanalysis, not observations. Rain error `[VERIFY]` |
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

## Hourly weather (`weather_forecast_hourly.csv`)

Columns `issued_at, ts, cell_id, temperature_c, relative_humidity_pct, precipitation_mm, heat_index_c, kind, is_simulated`, hourly, Manila time, one block per weather cell (`silip_ml.weather.cell_id`, `WEATHER_CELL_DEG = 0.1` `[VERIFY]`) that holds a transformer. One file, two kinds: `kind='archive'` is the observed hour (`issued_at = ts`); `kind='forecast'` is issued every 6 h (00:00, 06:00, 12:00, 18:00) for the next 72 h. Weather truth is simulated for 72 h past the last load interval (clear days, own stream `[SEED, 9002]`; load, household and outage data are not extended), so at the end of the run (dev and seed 8: 2026-05-26 23:45) the latest issue is 18:00 that day and covers the next 66 h (2026-05-27 00:00 to 2026-05-29 17:00). Archive rows stop at the end of the run. The simulator has one regional weather series, so every cell carries the same values. Features must read only rows with `issued_at` at or before the scoring time. It has its own random streams, so the other tables are byte-identical to runs without it: the 00:00 issues draw their in-run hours from `[SEED, 9001]`, and their post-run hours and the 06/12/18 issues from a stream keyed by issue time (`_weather.issue_rng`), so the 00:00 issues that features read are unchanged by the extra issues. Dev: 7 cells, 122,304 rows; test: 2 cells, 13,104 rows.
