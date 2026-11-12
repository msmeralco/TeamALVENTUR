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

-- The app role reads everything and inserts readings and outage data. No DELETE; UPDATE only on
-- household's place columns (granted below).
GRANT USAGE ON SCHEMA public TO silip_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO silip_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT ON TABLES TO silip_app;
-- load_sim fills household places on rows loaded before these columns existed (null only).
GRANT UPDATE (lat, lon, osm_way_id) ON household TO silip_app;
