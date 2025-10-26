# Reconstruction & Recovery Log

Date: 2025-10-25
Repository: MT5-Process-Core
Working directory: /home/felipe/MT5-Process-Core-full

## Summary
This document records the full recovery and preparation steps performed to clean Docker, recover the TimescaleDB data volume, make a portable DB backup, and harden filesystem/compose configuration to avoid permission problems during maintenance.

Short status:
- All project host bind-mount directories recreated and ownership fixed (UID/GID = from `.env` or current user).
- `docker-compose.yml` updated to run key services with host UID:GID.
- DB volume `mt5_db_data` verified and a dump exported to `./db_backup.dump`.
- Temporary DB container used for dump; it was removed after copy (forced removal required and performed).
- A helper script `scripts/fix_bind_mounts_permissions.sh` was added and executed to ensure directories and volume presence.

---

## Chronological actions and commands executed

1) Initial attempts to clean Docker and remove containers failed due to permission issues. Commands used, errors observed:

- `docker compose down -v --remove-orphans` (failed: .env missing initially)
- `sudo docker stop $(docker ps -aq) && sudo docker rm -f $(docker ps -aq) && sudo docker volume prune -f` (permission denied for several containers)

2) Permission troubleshooting & escalation:

- Restarted Docker service:
  - `sudo systemctl restart docker`
- Killed stuck processes (containerd / containerd-shim) and restarted systemd daemon when needed.
- When permissions persisted, used the "nuclear" approach of killing containerd-shim processes and restarting Docker.
- Rebooted host at user's request (`sudo reboot`) to clear remaining zombies.

3) Restored project infrastructure files which were missing (files ignored by git):

- Recreated folders and minimal `.env` files in repo root and `api/.env` and `env/.env.local`.
  - `/home/felipe/MT5-Process-Core-full/.env` created with required variables including `UID` and `GID`.

4) Verified Docker volumes after reboot and found `mt5_db_data` present:

- `sudo docker volume ls` listed `mt5_db_data` and other volumes.
- Inspected the volume by listing its contents using a temporary TimescaleDB image:
  - `sudo docker run --rm -it -v mt5_db_data:/var/lib/postgresql/data timescale/timescaledb:2.14.2-pg16 ls /var/lib/postgresql/data`
  - Output showed PostgreSQL data directories (e.g. `PG_VERSION`, `base`, `global`, `pg_wal`, etc.).

5) Exported DB (migration to repo directory):

- Spawned a temporary DB container using the existing volume:
  - `sudo docker run -d --name temp_pg -e POSTGRES_USER=trader -e POSTGRES_PASSWORD=trader123 -e POSTGRES_DB=mt5_trading -v mt5_db_data:/var/lib/postgresql/data timescale/timescaledb:2.14.2-pg16`
- Waited until DB accepted connections inside container:
  - `sudo docker exec temp_pg bash -c "until pg_isready -U trader -d mt5_trading; do sleep 1; done; echo 'ready'"`
- Created a dump in the container and copied it out:
  - `sudo docker exec temp_pg pg_dump -U trader -d mt5_trading -F c -f /tmp/db_backup.dump`
  - `sudo docker cp temp_pg:/tmp/db_backup.dump ./db_backup.dump`

Notes: `pg_dump` warned about circular FK constraints and continuous aggregates (TimescaleDB-specific). This is expected; restoring a TimescaleDB dump may require special care (see Restore notes below).

6) Cleanup of temp container and forced removal of remaining containers:

- There were permission errors removing `temp_pg` at first. Resolved by killing the `containerd-shim` process and then removing the container:
  - `sudo ps aux | grep containerd-shim` (identify shim PID)
  - `sudo kill -9 <PID>` for the shim
  - `sudo docker rm -f temp_pg`
- Forced removal of other containers and pruning volumes was performed:
  - `sudo docker stop $(sudo docker ps -aq) || true`
  - `sudo docker rm -f $(sudo docker ps -aq) || true`
  - `sudo docker volume prune -f`

7) Fixing host directories and permissions for bind mounts and volumes

- Added `scripts/fix_bind_mounts_permissions.sh` (committed to repo) and executed it with sudo. It:
  - Reads `.env` for `UID` and `GID` (falls back to current user ids).
  - Ensures the following host paths exist and are owned by `UID:GID` with mode `rwxrwxr-x` (775):
    - `db/init`
    - `docker/postgres.conf.d`
    - `scripts`
    - `api/logs`
    - `api/data_raw`
    - `ml/data`
    - `grafana/provisioning`
    - `loki`
    - `prometheus.yml` (touches file if missing)
    - `logs`
  - Ensures named volume `models_mt5` exists (creates it if missing).

8) Hardening compose file for permissions

- We updated `docker-compose.yml` to set `user: "${UID}:${GID}"` for critical services (db, api, tick-aggregator, indicators-worker, ml-trainer). This causes container processes to run with the host user's UID and GID so that bind-mounted data paths are writable without root ownership problems.

Files created/edited
- Created/edited:
  - `.env` (root of repo) — added application env vars + UID/GID
  - `api/.env` — minimal API env
  - `env/.env.local` — local env
  - `scripts/fix_bind_mounts_permissions.sh` — new helper script (executable)
  - `docs/RECONSTRUCTION_LOG.md` — this log file
  - Edited `docker-compose.yml` — added `user: "${UID}:${GID}"` for key services
- Backup file:
  - `./db_backup.dump` — the TimescaleDB dump (custom format). File present in repo root.

Commands run (high level)
- System & Docker control:
  - `sudo systemctl restart docker`
  - `sudo pkill -9 docker|containerd|dockerd|containerd-shim || true`
  - `sudo systemctl daemon-reload`
  - `sudo reboot` (performed by user)
- Cleanup & force remove:
  - `sudo docker stop $(sudo docker ps -aq) || true`
  - `sudo docker rm -f $(sudo docker ps -aq) || true`
  - `sudo docker volume prune -f`
- DB migration dump:
  - `sudo docker run -d --name temp_pg -e POSTGRES_USER=trader -e POSTGRES_PASSWORD=trader123 -e POSTGRES_DB=mt5_trading -v mt5_db_data:/var/lib/postgresql/data timescale/timescaledb:2.14.2-pg16`
  - `sudo docker exec temp_pg bash -c "until pg_isready -U trader -d mt5_trading; do sleep 1; done; echo 'ready'"`
  - `sudo docker exec temp_pg pg_dump -U trader -d mt5_trading -F c -f /tmp/db_backup.dump`
  - `sudo docker cp temp_pg:/tmp/db_backup.dump ./db_backup.dump`
- Permissions fix script:
  - `sudo chmod +x scripts/fix_bind_mounts_permissions.sh`
  - `sudo ./scripts/fix_bind_mounts_permissions.sh`

Validation & current state
- `db_backup.dump` exists at repo root.
- `mt5_db_data` Docker volume exists and contained Postgres data.
- The repo now contains helper scripts and `docker-compose.yml` is adapted to avoid permission issues (UID/GID usage).
- No containers are currently running on the host.

Important notes and restore advice
- TimescaleDB specifics: the dump included warnings about circular FK constraints and continuous aggregates. When restoring to a TimescaleDB instance, recommended steps:
  1. Create the DB & user (matching original roles).
  2. Install the `timescaledb` extension BEFORE restoring (in the target database):
     - `CREATE EXTENSION IF NOT EXISTS timescaledb;`
  3. Use `pg_restore` for the custom-format file. Consider `--disable-triggers` or restore schema first, then data.
  4. For continuous aggregates, see TimescaleDB docs: you may need to recreate policies or refresh materialized views after restore.

Example restore (on fresh TimescaleDB):

```bash
# create db
createdb -U trader mt5_trading
# ensure extension
psql -U trader -d mt5_trading -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
# restore
pg_restore -U trader -d mt5_trading ./db_backup.dump
```

If you expect to run the project from a different path than `/home/felipe/MT5-Process-Core-full` note that several systemd units and scripts in the repo contain absolute paths like `/home/felipe/MT5-Process-Core-full` and `/home/felipe/backups`. Those will need to be updated to the new path or refactored to use a `PROJECT_ROOT` environment variable. Files to inspect (examples):
- `systemd/*.service` entries (WorkingDirectory, ExecStart)
- `README.md` and docs referencing `/home/felipe/MT5-Process-Core-full`
- `scripts/*` that `cd` into hardcoded paths

I can prepare a small automated sed script to update those absolute paths if you confirm the new repo location.

Next recommended steps
1. (If you want) Start the full stack now:

```bash
sudo docker compose up -d --build
```

2. Wait for `mt5_db` to report healthy (use `docker compose ps` / `docker ps` or checks in `docker-compose.yml`).
3. Connect to DB and run quick verifications:

```bash
sudo docker exec -it <db-container-name> psql -U trader -d mt5_trading -c "SELECT COUNT(*) FROM market_data;"
sudo docker exec -it <db-container-name> psql -U trader -d mt5_trading -c "SELECT * FROM market_data ORDER BY ts DESC LIMIT 5;"
```

4. Optionally run `scripts/fix_bind_mounts_permissions.sh` on any other host where you move the repo after updating `.env` UID/GID.

---

If you want, I can now:
- A) Bring the stack up and run the DB checks (recommended), or
- B) Create a sed-based script to update absolute paths across the repo to the new location you used, or
- C) Prepare a short `README_RECOVERY.md` with restore commands and automated recovery steps for on-call use.

Which do you want next?