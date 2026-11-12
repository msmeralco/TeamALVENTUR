# data

Nothing here is committed except this file and `osm/`. Everything else can be regenerated.

- `raw/`: real exports (smart meters, check meters, outages). Never committed, never read by agents. SINs only as `sin_hash`.
- `osm/`: committed OpenStreetMap snapshot of real transformer sites (ODbL 1.0); see `osm/README.md`.
- `sim/`: output of `make sim` (`silip_ml.readings.simulate`, fixed seed). Every row has `is_simulated=True`.
- `processed/`: aggregated tables built from `raw/` or `sim/` by `silip_ml.readings.aggregate`.
