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

-- The app role reads everything and inserts readings and outage data. No UPDATE or DELETE.
GRANT USAGE ON SCHEMA public TO silip_app;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO silip_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT ON TABLES TO silip_app;
