"""
Phase 3, Step 2: extract all 6 OLTP tables to MinIO raw zone, in parallel.

Generalizes the single-table pattern proven in phase3_extract_customers.py.
Each table gets its own task; tasks have no dependencies on each other,
so Airflow's LocalExecutor runs them concurrently.

NOTE: phase3_extract_customers.py (the single-table version) is left in
place intentionally -- it's the "thin slice" we built and verified first,
and is referenced in PHASE1-3 documentation as the original proof of concept.
This DAG is what actually gets used/scheduled going forward.
"""
from __future__ import annotations

import io
import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-platform",
    "retries": 1,
}

# Every table we extract, with no transformation -- just a 1:1 copy from
# Postgres into raw Parquet. Order doesn't matter here since these are
# independent reads, not writes with foreign-key dependencies.
TABLES = ["customers", "products", "campaigns", "orders", "order_items", "payments"]


def make_extract_fn(table_name: str):
    """Returns a closure so each PythonOperator gets its own table name
    baked in, without needing op_kwargs juggling for this simple case."""

    def extract_table_to_minio():
        import pandas as pd
        import psycopg2
        from minio import Minio

        conn = psycopg2.connect(
            host=os.environ["OLTP_PG_HOST"],
            dbname=os.environ["OLTP_PG_DB"],
            user=os.environ["OLTP_PG_USER"],
            password=os.environ["OLTP_PG_PASSWORD"],
        )
        df = pd.read_sql(f"SELECT * FROM {table_name};", conn)
        conn.close()
        print(f"Extracted {len(df)} rows from postgres-oltp.{table_name}")

        buffer = io.BytesIO()
        df.to_parquet(buffer, engine="pyarrow", index=False)
        buffer.seek(0)
        size_bytes = buffer.getbuffer().nbytes
        print(f"Converted to Parquet, {size_bytes / 1024 / 1024:.2f} MB")

        endpoint = os.environ["MINIO_ENDPOINT"].replace("http://", "")
        client = Minio(
            endpoint,
            access_key=os.environ["MINIO_ROOT_USER"],
            secret_key=os.environ["MINIO_ROOT_PASSWORD"],
            secure=False,
        )

        object_name = (
            f"raw/{table_name}/extract_date={datetime.utcnow().date()}/{table_name}.parquet"
        )
        client.put_object(
            "retail-platform",
            object_name,
            buffer,
            length=size_bytes,
            content_type="application/octet-stream",
        )
        print(f"Wrote to MinIO: retail-platform/{object_name}")

    return extract_table_to_minio


with DAG(
    dag_id="phase3_extract_all_tables",
    description="Extracts all 6 OLTP tables to MinIO raw zone, one parallel task per table",
    default_args=default_args,
    schedule=None,  # trigger manually for now
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["phase3", "batch", "extraction"],
) as dag:

    for table in TABLES:
        PythonOperator(
            task_id=f"extract_{table}",
            python_callable=make_extract_fn(table),
        )
