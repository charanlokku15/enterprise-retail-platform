# Enterprise Retail Data Platform

A batch + streaming data platform built to demonstrate the full modern data
engineering lifecycle — ingestion, orchestration, data quality, batch
processing, streaming, dimensional modeling, analytics engineering, and
dashboarding — on a $0 local stack that mirrors real cloud architecture.

See `ARCHITECTURE.md` (coming in a later phase) for the full diagram.
This README covers **Phase 1: Infrastructure** only.

## Phase 1 scope

Goal: every core service starts successfully and Airflow can reach all of them.

| Service | Role | Port |
|---|---|---|
| `postgres-airflow` | Airflow's own metadata DB (internal) | — |
| `postgres-oltp` | Simulated retailer OLTP source DB | `5433` |
| `minio` | S3-compatible object storage (raw/processed/curated/archive) | `9000` (API), `9001` (console) |
| `airflow-webserver` / `airflow-scheduler` | Orchestration (LocalExecutor) | `8080` |
| DuckDB | Embedded warehouse file — **not a container**, just `./warehouse/retail.duckdb` | — |

Not included yet (later phases): FastAPI service, Spark, dbt, Kafka, Great
Expectations checks, Grafana. Folders for these already exist as
placeholders so the repo structure doesn't need to change later.

## Prerequisites

- Docker + Docker Compose v2
- ~4GB free RAM for this phase (more once Spark/Kafka are added)
- Ports 5433, 8080, 9000, 9001 free on your machine

## Run it

```bash
cp .env.example .env   # if you're starting from a template; otherwise .env is already populated
docker compose up -d
```

First boot takes a few minutes — Airflow has to migrate its metadata DB and
install the extra Python packages listed in `_PIP_ADDITIONAL_REQUIREMENTS`.

Watch it come up:
```bash
docker compose ps
docker compose logs -f airflow-init    # should exit 0 when done
```

## Verify everything actually works

This is the point of Phase 1 — don't just confirm containers are "Up", prove
they can talk to each other.

1. **Airflow UI** — open http://localhost:8080 (`admin` / `admin`)
2. **MinIO console** — open http://localhost:9001 (`minioadmin` / `minioadmin123`)
   You should see one bucket, `retail-platform`, containing `raw/`,
   `processed/`, `curated/`, `archive/` prefixes (created by `minio-init`).
3. **OLTP Postgres** — connect directly to confirm the schema landed:
   ```bash
   docker compose exec postgres-oltp psql -U retail_app -d retail_oltp -c "\dt"
   ```
   You should see `customers`, `products`, `orders`, `order_items`,
   `payments`, `campaigns` (empty — Phase 2 loads data into them).
4. **End-to-end smoke test** — run the included DAG, which checks Postgres,
   MinIO, *and* DuckDB from inside Airflow itself:
   ```bash
   make smoke-test
   ```
   Then check the run in the Airflow UI under
   `phase1_infra_smoke_test` — all three tasks
   (`check_oltp_postgres`, `check_minio`, `check_duckdb`) should go green.

If all three tasks pass, Phase 1 is done: every service in the architecture
starts, and Airflow can reach Postgres, MinIO, and DuckDB. Phase 2
(data generation) builds directly on this.

## Common issues

- **Port already in use** — something else on your machine is on 5432/8080/9000.
  Either stop it or change the port mapping in `docker-compose.yml`.
- **`airflow-init` fails on `users create`** — harmless if the user already
  exists from a previous run (`|| true` in the entrypoint handles this).
- **MinIO healthcheck never passes** — make sure `curl` is available inside
  the MinIO image (it is, by default, in the version pinned here); if you
  swap the image tag, re-check this.
- **Slow first boot** — `_PIP_ADDITIONAL_REQUIREMENTS` installs packages into
  the Airflow containers on every fresh start. This is fine for Phase 1, but
  once the dependency list stabilizes, move it into a custom `Dockerfile` so
  startup doesn't reinstall packages every time (`docker compose up`'s init
  step will say so by being slow — that's the signal to switch).

## Reset everything

```bash
make reset
```
Drops all containers, volumes, the DuckDB file, and MinIO's local data —
back to a completely clean slate.

## Repo structure

```
enterprise-retail-platform/
├── docker-compose.yml
├── .env
├── Makefile
├── requirements.txt
├── airflow/
│   └── dags/
│       └── phase1_infra_smoke_test.py
├── scripts/
│   └── init_oltp_schema.sql      # auto-run by postgres-oltp on first boot
├── data/
│   ├── generated/                 # Phase 2: Faker-generated source data
│   └── raw/                       # Phase 2: vendor-style CSV landing zone
├── warehouse/                      # DuckDB file lives here (gitignored)
├── fastapi_app/                    # Phase 3: Marketing/Customer API
├── spark/jobs/                     # Phase 3+: batch + streaming Spark jobs
├── dbt/                            # Phase 4: staging/intermediate/mart models
├── great_expectations/             # Phase 8: data quality suites
└── kafka/                          # Phase 6+: streaming config
```
