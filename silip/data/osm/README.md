# data/osm

`transformers.csv`: real distribution-transformer sites in and around Metro Manila, used by the simulator only to place transformers on the map. Load, homes, risk and outages stay simulated (`is_simulated=True`).

- Source: OpenStreetMap via the Overpass API (`https://overpass-api.de/api/interpreter`)
- Fetched: 2026-11-12
- Licence: © OpenStreetMap contributors, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/1-0/)
- Query (bbox south, west, north, east):

```
[out:json][timeout:60];
(
  node["power"="transformer"](14.35,120.90,14.80,121.15);
  node["power"="pole"]["transformer"](14.35,120.90,14.80,121.15);
);
out body;
```

- Kept: nodes whose `transformer` tag is `distribution` or absent, and that are operated by Meralco (`operator` or `operator:wikidata=Q6817918`) or tagged `transformer=distribution` with no operator. 224 nodes returned, 203 kept.
- Columns: `osm_node_id, lat, lon, operator, power, transformer`
- Regenerate: `uv run python -m silip_ml.readings.osm_transformers` (rule in `is_meralco_distribution`)

## `buildings.csv`

Real building centres near each transformer site, used by the simulator only to place simulated households on real roofs. Only the centre point and OSM way ID are kept, never tags or addresses. Households, SINs and clamps stay simulated.

- Source, licence: same as above (Overpass API, © OpenStreetMap contributors, ODbL 1.0). Fetched 2026-11-12.
- Query: every `way["building"]` within 150 m of the transformer nodes in `transformers.csv` (`node(id:...)->.sites; way["building"](around.sites:150); out center;`).
- Kept: the 80 nearest buildings per site. 6,850 raw, 4,713 kept, 9,717 site-building rows; every site has at least 2.
- Columns: `osm_node_id` (site), `osm_way_id`, `lat`, `lon`, `distance_m`
- Regenerate: `uv run python -m silip_ml.readings.osm_buildings`
