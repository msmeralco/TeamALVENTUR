# Local PostgreSQL replica

The local app uses PostgreSQL 18 in Docker, matching the Neon server major version. The database is bound to `127.0.0.1:55432` and persists in the Compose `postgres-data` volume.

`env/env.dev` remains the Neon source configuration. The ignored `silip/.env.local` overrides file-based database settings for local development: `DATABASE_URL` is the restricted local `silip_app` connection, and `DATABASE_DIRECT_URL` is the local database owner connection for migrations. Shell environment variables take precedence over all env files. The settings file order is `.env`, `../env/env.dev`, then `.env.local`.

The ignored `.local/postgres.env` contains Docker bootstrap credentials. Keep it with `.env.local`; neither file belongs in Git. The private `.local/neon.snapshot.dump` is the consistent source snapshot used for the initial restore. All ten public tables were copied with data; source owners and ACLs were omitted so the local owner could apply `db/schema.sql` and grant the local app its required privileges. No migration was applied to Neon.

From `silip/`:

```sh
docker compose up -d --wait db
make db
AUTH_DISABLED=true DATA_SOURCE=neon make api
```

`make db` applies the additive schema through the owner URL in `.env.local`. `AUTH_DISABLED=true` is for localhost development only and is refused in Lambda. Stop the local database with `docker compose stop db`; start it with the first command above. Stopping retains data. Do not remove the volume when you want to keep the replica.

`DATA_SOURCE=neon` preserves the copied simulated risk-map and household-load dataset. The name identifies the table strategy, not a forced remote connection; its database is now local. Device registration and the Devices telemetry view query the local registry and `reading` tables directly. Set `DATA_SOURCE=clamp` and restart the API when you want the existing risk map and household usage to use newly ingested clamp readings instead. The source snapshot had no electrical `reading` rows, so that view starts empty.

Cloud Lambda cannot connect to a database bound to your laptop's loopback interface. Local handler checks use this replica; cloud ingestion requires the cloud database migration and deployment described in [IoT management](iot-management.md).
