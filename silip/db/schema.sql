-- SILIP schema (Neon Postgres). Additive only: CREATE ... IF NOT EXISTS, never DROP.
-- Apply once as the database OWNER (Neon SQL Editor, or `make db` with an owner URL).
-- The app role silip_app cannot create tables; it only reads and inserts (grants at the end).
-- SINs exist only as salted hashes. Every table carries is_simulated.

CREATE TABLE IF NOT EXISTS transformer (
    transformer_id  text PRIMARY KEY,
    rated_kva       numeric NOT NULL CHECK (rated_kva > 0),
    homes           integer NOT NULL CHECK (homes >= 0),
    coverage_pct    numeric NOT NULL CHECK (coverage_pct BETWEEN 0 AND 1),
    lat             double precision NOT NULL,
    lon             double precision NOT NULL,
    is_simulated    boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS household (
    sin_hash        char(64) PRIMARY KEY,
    transformer_id  text NOT NULL REFERENCES transformer,
    has_clamp       boolean NOT NULL DEFAULT false,
    is_simulated    boolean NOT NULL DEFAULT false
);

-- Links a Cognito user (sub) to the one household it may see.
CREATE TABLE IF NOT EXISTS household_account (
    cognito_sub     text PRIMARY KEY,
    sin_hash        char(64) NOT NULL REFERENCES household,
    linked_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS reading (
    sin_hash             char(64) NOT NULL REFERENCES household,
    transformer_id       text NOT NULL REFERENCES transformer,
    ts                   timestamptz NOT NULL,
    voltage_v            real NOT NULL,
    current_a            real NOT NULL,
    power_kw             real NOT NULL,
    power_factor         real NOT NULL,
    energy_kwh_interval  real NOT NULL,
    event                text CHECK (event IN ('last_gasp')),
    is_simulated         boolean NOT NULL DEFAULT false,
    PRIMARY KEY (sin_hash, ts)
);
CREATE INDEX IF NOT EXISTS reading_transformer_ts ON reading (transformer_id, ts);

CREATE TABLE IF NOT EXISTS smart_meter_interval (
    sin_hash        char(64) NOT NULL REFERENCES household,
    transformer_id  text NOT NULL REFERENCES transformer,
    ts              timestamptz NOT NULL,
    energy_kwh      real NOT NULL,
    is_simulated    boolean NOT NULL DEFAULT false,
    PRIMARY KEY (sin_hash, ts)
);

CREATE TABLE IF NOT EXISTS outage (
    outage_id       text PRIMARY KEY,
    transformer_id  text NOT NULL REFERENCES transformer,
    start_ts        timestamptz NOT NULL,
    cause           text NOT NULL,
    duration_min    integer,  -- null while open
    is_simulated    boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS outage_signal (
    outage_id       text NOT NULL REFERENCES outage,
    kind            text NOT NULL CHECK (kind IN ('last_gasp', 'report')),
    ts              timestamptz NOT NULL,
    lat             double precision NOT NULL,
    lon             double precision NOT NULL,
    is_simulated    boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS outage_signal_outage ON outage_signal (outage_id);

-- Tables below have no is_simulated default, so an insert that omits the flag fails.
-- CREATE ... IF NOT EXISTS: this only applies where the table does not exist yet.

-- OSM node the site was taken from (data/osm, ODbL); null for sites not from OSM.
ALTER TABLE transformer ADD COLUMN IF NOT EXISTS osm_node_id bigint;

-- Whole-transformer kW (DATA_SOURCE=neon). Separate from `reading`, which needs voltage/current.
CREATE TABLE IF NOT EXISTS transformer_load (
    transformer_id  text NOT NULL REFERENCES transformer,
    ts              timestamptz NOT NULL,
    transformer_kw  real NOT NULL,
    is_simulated    boolean NOT NULL,
    PRIMARY KEY (transformer_id, ts)
);

-- Per-home average kW per 15 minutes (DATA_SOURCE=neon household usage).
CREATE TABLE IF NOT EXISTS household_load (
    sin_hash        char(64) NOT NULL REFERENCES household,
    transformer_id  text NOT NULL REFERENCES transformer,
    ts              timestamptz NOT NULL,
    power_kw        real NOT NULL,
    is_simulated    boolean NOT NULL,
    PRIMARY KEY (sin_hash, ts)
);

-- Where a household is, for the map: an OSM building centre (osm_way_id, ODbL) or a spot near its
-- transformer when no building is mapped. Shown as a device point, never with usage.
ALTER TABLE household ADD COLUMN IF NOT EXISTS lat double precision;
ALTER TABLE household ADD COLUMN IF NOT EXISTS lon double precision;
ALTER TABLE household ADD COLUMN IF NOT EXISTS location_label text;
ALTER TABLE household ADD COLUMN IF NOT EXISTS osm_way_id bigint;

-- One retrofit clamp per opted-in household (one SIN, one transformer). clamp_id is the node's
-- MQTT client ID. last_seen_at is the latest reading the node sent.
CREATE TABLE IF NOT EXISTS clamp (
    clamp_id        text PRIMARY KEY,
    sin_hash        char(64) NOT NULL UNIQUE REFERENCES household,
    ct_model        text NOT NULL,
    installed_at    timestamptz NOT NULL,
    last_seen_at    timestamptz,
    is_simulated    boolean NOT NULL
);

-- Scheduled risk scoring (silip.scoring). Insert-only: a run and all its rows go in one
-- transaction, and the API reads the latest complete run. Transformer totals only: no sin_hash and
-- no per-household rows. run_id is a uuid4 from the job (text, so no sequence grant is needed).
-- as_of is the latest 15-minute load interval scored, by the data's own clock.
CREATE TABLE IF NOT EXISTS score_run (
    run_id          text PRIMARY KEY,
    as_of           timestamptz NOT NULL,
    started_at      timestamptz NOT NULL,
    finished_at     timestamptz NOT NULL,
    status          text NOT NULL CHECK (status IN ('complete', 'failed')),
    forecaster      text NOT NULL,
    risk_scorer     text NOT NULL,
    transformers    integer NOT NULL,
    error           text,  -- exception class name only, never a message
    is_simulated    boolean NOT NULL
);
-- One complete run per data interval and strategy pair: a rerun of the same bucket is refused.
CREATE UNIQUE INDEX IF NOT EXISTS score_run_bucket
    ON score_run (as_of, forecaster, risk_scorer) WHERE status = 'complete';

CREATE TABLE IF NOT EXISTS transformer_score (
    run_id          text NOT NULL REFERENCES score_run,
    transformer_id  text NOT NULL REFERENCES transformer,
    tier            text NOT NULL CHECK (tier IN ('OK', 'Watch', 'Critical')),
    reasons         text[] NOT NULL,
    confidence      real NOT NULL,
    peak_load_pct   real NOT NULL,
    coverage_pct    real NOT NULL,
    is_simulated    boolean NOT NULL,
    PRIMARY KEY (run_id, transformer_id)
);

-- The 24 h forecast behind each score, for the transformer card.
CREATE TABLE IF NOT EXISTS forecast_point (
    run_id          text NOT NULL REFERENCES score_run,
    transformer_id  text NOT NULL REFERENCES transformer,
    ts              timestamptz NOT NULL,
    kw_pred         real NOT NULL,
    is_simulated    boolean NOT NULL,
    PRIMARY KEY (run_id, transformer_id, ts)
);

-- The app role reads everything and inserts readings and outage data. No DELETE; UPDATE only on
-- household's place columns (granted below). The score tables above get SELECT, INSERT only, so
-- the scoring job never rewrites a run. The owner applies this file (Neon SQL Editor or `make db`).
GRANT USAGE ON SCHEMA public TO silip_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO silip_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT ON TABLES TO silip_app;
-- load_sim fills household places on rows loaded before these columns existed (null only).
GRANT UPDATE (lat, lon, osm_way_id) ON household TO silip_app;

-- Motion is a reported signal for review, never proof of theft.
ALTER TABLE reading ADD COLUMN IF NOT EXISTS motion jsonb;
GRANT UPDATE (has_clamp, transformer_id, lat, lon, location_label) ON household TO silip_app;
GRANT UPDATE (last_seen_at) ON clamp TO silip_app;

-- Dashboard-issued device keys are stored only as hashes.
ALTER TABLE clamp ADD COLUMN IF NOT EXISTS device_key_hash text;
GRANT UPDATE (device_key_hash) ON clamp TO silip_app;

-- Decision dashboard (ADR 0006 weather, ADR 0007 EV exposure). Insert-only for the app role.
-- Hourly weather per grid cell (silip_ml.weather.cell_id). A forecast is never rewritten: each
-- fetch is a new issued_at, and readers take the latest issue at or before their scoring time.
CREATE TABLE IF NOT EXISTS weather_hourly (
    cell_id                text NOT NULL,
    lat                    double precision NOT NULL,
    lon                    double precision NOT NULL,
    ts                     timestamptz NOT NULL,
    issued_at              timestamptz NOT NULL,
    kind                   text NOT NULL CHECK (kind IN ('forecast', 'archive')),
    temperature_c          real,
    relative_humidity_pct  real,
    precipitation_mm       real,
    heat_index_c           real,
    source                 text NOT NULL DEFAULT 'open-meteo',
    is_simulated           boolean NOT NULL,
    PRIMARY KEY (cell_id, ts, kind, issued_at)
);
CREATE INDEX IF NOT EXISTS weather_hourly_issued ON weather_hourly (kind, issued_at);

-- DOE EV charging stations (data/evcs_locations.csv). station_id is the first 16 hex of
-- sha256(name|lat|lon); source_sha256 is the file the row came from.
CREATE TABLE IF NOT EXISTS ev_charger (
    station_id      text PRIMARY KEY,
    name            text NOT NULL,
    region          text,
    province        text,
    city            text,
    barangay        text,
    lat             double precision NOT NULL,
    lon             double precision NOT NULL,
    source          text NOT NULL,
    source_sha256   text NOT NULL,
    loaded_at       timestamptz NOT NULL,
    is_simulated    boolean NOT NULL DEFAULT false
);

-- EV adoption statistics (data/ev_adoption.csv), one value per period, place, metric and class.
CREATE TABLE IF NOT EXISTS ev_adoption (
    period           text NOT NULL,
    geography_level  text NOT NULL,
    geography        text NOT NULL,
    metric           text NOT NULL
        CHECK (metric IN ('ev_sales', 'ev_registrations', 'ev_stock', 'ev_share_of_sales')),
    vehicle_class    text NOT NULL,
    value            numeric NOT NULL,
    unit             text NOT NULL,
    source_url       text,
    retrieved_at     timestamptz,
    is_simulated     boolean NOT NULL,
    PRIMARY KEY (period, geography_level, geography, metric, vehicle_class)
);

-- DOE stations near each transformer, per station file version.
CREATE TABLE IF NOT EXISTS transformer_ev_exposure (
    transformer_id     text NOT NULL REFERENCES transformer,
    radius_m           integer NOT NULL,
    stations_within    integer NOT NULL,
    nearest_station_m  real,  -- null when there are no stations
    source_sha256      text NOT NULL,
    computed_at        timestamptz NOT NULL,
    is_simulated       boolean NOT NULL,
    PRIMARY KEY (transformer_id, source_sha256)
);

-- Dashboard fields per score: when the peak is, the rules-table action, the per-feature drivers,
-- and clamp health. Null on runs scored before these columns existed.
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS peak_ts timestamptz;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS action text;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS drivers jsonb;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS heat_index_max_c real;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS ev_evening_step_kw real;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS homes_reporting integer;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS clamps_installed integer;
ALTER TABLE transformer_score ADD COLUMN IF NOT EXISTS clamps_online integer;
-- Which weather issue the run used and how fresh it was (fresh, stale, missing).
ALTER TABLE score_run ADD COLUMN IF NOT EXISTS weather_issued_at timestamptz;
ALTER TABLE score_run ADD COLUMN IF NOT EXISTS weather_status text;

-- The tables above were created after the bulk grant, so grant them explicitly (SELECT, INSERT).
GRANT SELECT, INSERT ON weather_hourly, ev_charger, ev_adoption, transformer_ev_exposure
    TO silip_app;

-- DOE station detail (data/evcs_stations_detail.csv, data/evcs_plugs.csv), joined to ev_charger on
-- station_id. Public site facts only: the DOE contact, e-mail, street view, equipment serial and
-- free-text fields are never loaded. Null on stations loaded without the detail files.
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS doe_station_number text;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS address text;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS classification text;  -- CUCS charging, BSS swap
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS n_chargepoints integer;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS n_ac integer;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS n_dc integer;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS n_plugs integer;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS max_capacity_kw real;  -- largest plug with a known kW
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS price_min_php_kwh real;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS price_max_php_kwh real;
ALTER TABLE ev_charger ADD COLUMN IF NOT EXISTS hours text;
-- The loader fills the detail of stations already loaded (INSERT ... ON CONFLICT DO UPDATE of
-- exactly these columns); everything else on ev_charger stays insert-only.
GRANT UPDATE (doe_station_number, address, classification, n_chargepoints, n_ac, n_dc, n_plugs,
    max_capacity_kw, price_min_php_kwh, price_max_php_kwh, hours) ON ev_charger TO silip_app;

-- One row per DOE plug. plug_id is the DOE label plus its occurrence in the station
-- ("Type 2 - Plug 1 #2"); price_php_kwh only for per-kWh pricing.
CREATE TABLE IF NOT EXISTS ev_plug (
    station_id     text NOT NULL REFERENCES ev_charger,
    plug_id        text NOT NULL,
    mode           text,
    protocol       text,
    capacity_kw    real,
    status         text,  -- operational | out_of_service
    price_php_kwh  real,
    source_sha256  text NOT NULL,
    loaded_at      timestamptz NOT NULL,
    is_simulated   boolean NOT NULL DEFAULT false,
    PRIMARY KEY (station_id, plug_id)
);

ALTER TABLE transformer_ev_exposure ADD COLUMN IF NOT EXISTS dc_stations_within integer;
ALTER TABLE transformer_ev_exposure ADD COLUMN IF NOT EXISTS max_capacity_kw_within real;

GRANT SELECT, INSERT ON ev_plug TO silip_app;
