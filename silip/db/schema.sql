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
