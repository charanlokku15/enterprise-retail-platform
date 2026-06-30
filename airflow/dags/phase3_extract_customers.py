"""
Phase 3, Step 1: extract customers from postgres-oltp, write raw Parquet to MinIO.

This is intentionally the simplest possible slice of the batch pipeline --
one table, no transformation, just Postgres -> Parquet -> MinIO raw zone.
Once this works end to end, the same pattern extends to the other 5 tables.
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


def extract_customers_to_minio():
    import pandas as pd
    import psycopg2
    from minio import Minio

    # --- Extract from Postgres ---
    conn = psycopg2.connect(
        host=os.environ["OLTP_PG_HOST"],
        dbname=os.environ["OLTP_PG_DB"],
        user=os.environ["OLTP_PG_USER"],
        password=os.environ["OLTP_PG_PASSWORD"],
    )
    df = pd.read_sql("SELECT * FROM customers;", conn)
    conn.close()
    print(f"Extracted {len(df)} rows from postgres-oltp.customers")

    # --- Convert to Parquet in memory (no local disk needed) ---
    buffer = io.BytesIO()
    df.to_parquet(buffer, engine="pyarrow", index=False)
    buffer.seek(0)
    size_bytes = buffer.getbuffer().nbytes
    print(f"Converted to Parquet, {size_bytes / 1024 / 1024:.2f} MB")

    # --- Write to MinIO raw zone ---
    endpoint = os.environ["MINIO_ENDPOINT"].replace("http://", "")
    client = Minio(
        endpoint,
        access_key=os.environ["MINIO_ROOT_USER"],
        secret_key=os.environ["MINIO_ROOT_PASSWORD"],
        secure=False,
    )

    object_name = f"raw/customers/extract_date={datetime.utcnow().date()}/customers.parquet"
    client.put_object(
        "retail-platform",
        object_name,
        buffer,
        length=size_bytes,
        content_type="application/octet-stream",
    )
    print(f"Wrote to MinIO: retail-platform/{object_name}")


with DAG(
    dag_id="phase3_extract_customers",
    description="Extracts customers from postgres-oltp and writes raw Parquet to MinIO",
    default_args=default_args,
    schedule=None,  # trigger manually for now
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["phase3", "batch", "extraction"],
) as dag:

    extract_task = PythonOperator(
        task_id="extract_customers_to_minio",
        python_callable=extract_customers_to_minio,
    )
