"""
Phase 1 smoke-test DAG.

Goal: prove every piece of infrastructure is reachable from Airflow
before any real pipeline logic gets written.

    check_oltp_postgres   -> can Airflow query the OLTP source?
    check_minio           -> can Airflow list/write to the MinIO buckets?
    check_duckdb          -> can Airflow open and write to the DuckDB file?

If all three tasks go green, Phase 1 is done: every service in the
architecture diagram starts, and Airflow can talk to all of them.
"""
from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-platform",
    "retries": 1,
}


def check_oltp_postgres():
    import psycopg2

    conn = psycopg2.connect(
        host=os.environ["OLTP_PG_HOST"],
        dbname=os.environ["OLTP_PG_DB"],
        user=os.environ["OLTP_PG_USER"],
        password=os.environ["OLTP_PG_PASSWORD"],
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' ORDER BY table_name;
        """
    )
    tables = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    expected = {"customers", "products", "orders", "order_items", "payments", "campaigns"}
    missing = expected - set(tables)
    if missing:
        raise RuntimeError(f"OLTP schema missing tables: {missing}")
    print(f"OLTP Postgres reachable. Tables found: {tables}")


def check_minio():
    import io

    from minio import Minio

    endpoint = os.environ["MINIO_ENDPOINT"].replace("http://", "")
    client = Minio(
        endpoint,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=False,
    )

    bucket = "retail-platform"
    if not client.bucket_exists(bucket):
        raise RuntimeError(f"MinIO bucket '{bucket}' does not exist yet")

    # mc mb -p creates ONE bucket with folder-prefixes inside it
    # (S3 has a flat namespace -- "raw/", "curated/" etc. are just key
    # prefixes, not separate buckets), so check for those prefixes here.
    existing_prefixes = {
        obj.object_name.rstrip("/")
        for obj in client.list_objects(bucket, recursive=False)
    }
    expected_zones = {"raw", "processed", "curated", "archive"}
    missing = expected_zones - existing_prefixes
    if missing:
        raise RuntimeError(
            f"MinIO bucket '{bucket}' missing zone prefixes: {missing}. "
            f"Found: {existing_prefixes}"
        )

    # Write + read back a tiny marker object to prove read/write works,
    # not just that the bucket and prefixes exist.
    marker = f"phase1-smoke-test-{datetime.utcnow().isoformat()}".encode()
    client.put_object(
        bucket,
        "raw/_smoke_test/marker.txt",
        io.BytesIO(marker),
        length=len(marker),
    )
    print(f"MinIO reachable. Bucket '{bucket}' zones found: {existing_prefixes}")


def check_duckdb():
    import duckdb

    path = os.environ["DUCKDB_PATH"]
    con = duckdb.connect(path)
    con.execute(
        "CREATE TABLE IF NOT EXISTS _smoke_test (checked_at TIMESTAMP)"
    )
    con.execute("INSERT INTO _smoke_test VALUES (now())")
    result = con.execute("SELECT count(*) FROM _smoke_test").fetchone()
    con.close()
    print(f"DuckDB reachable at {path}. Smoke-test row count: {result[0]}")


with DAG(
    dag_id="phase1_infra_smoke_test",
    description="Verifies Postgres (OLTP), MinIO, and DuckDB are all reachable",
    default_args=default_args,
    schedule=None,  # trigger manually
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["phase1", "infra", "smoke-test"],
) as dag:

    t1 = PythonOperator(task_id="check_oltp_postgres", python_callable=check_oltp_postgres)
    t2 = PythonOperator(task_id="check_minio", python_callable=check_minio)
    t3 = PythonOperator(task_id="check_duckdb", python_callable=check_duckdb)

    [t1, t2, t3]
