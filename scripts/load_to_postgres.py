"""
Phase 2, Step 7: load generated CSVs into postgres-oltp.

Loads ONE table per invocation (--table customers, --table orders, etc.)
so each load can be verified before moving to the next.

Loads in dependency order: customers, products, campaigns first (no FKs),
then orders (needs customers), then order_items (needs orders+products),
then payments (needs orders).

order_items.csv has a line_total column that does NOT exist in the
Postgres schema -- it's intentionally dropped here (see Step 21 notes).
"""
import argparse
import io

import pandas as pd
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "dbname": "retail_oltp",
    "user": "retail_app",
    "password": "retail_app_pw",
}

# Column order here must exactly match the Postgres table's column order.
TABLE_SPECS = {
    "customers": ["customer_id", "name", "email", "phone", "city", "state",
                  "country", "signup_date", "loyalty_tier", "updated_at"],
    "products": ["product_id", "product_name", "category", "brand",
                 "price", "cost", "updated_at"],
    "campaigns": ["campaign_id", "campaign_name", "channel", "budget",
                  "start_date", "end_date"],
    "orders": ["order_id", "customer_id", "order_date", "order_status",
               "order_amount", "payment_method"],
    # NOTE: line_total deliberately excluded -- not a column in the
    # Postgres schema. See Step 21 for why it's computed in dbt instead.
    "order_items": ["order_item_id", "order_id", "product_id",
                     "quantity", "unit_price"],
    "payments": ["payment_id", "order_id", "payment_date",
                 "payment_status", "amount"],
}

# Columns that contain NULLs and must be read back as pandas' nullable
# integer type ("Int64", capital I) instead of the default float64 --
# otherwise any column with missing values round-trips through CSV as
# "3279.0" instead of "3279", which Postgres' BIGINT rejects outright.
NULLABLE_INT_COLUMNS = {
    "orders": ["customer_id"],
}

CHUNK_SIZE = 100_000


def load_table(table: str, truncate: bool):
    cols = TABLE_SPECS[table]
    csv_path = f"data/generated/{table}.csv"

    dtype_overrides = {}
    for col in NULLABLE_INT_COLUMNS.get(table, []):
        dtype_overrides[col] = "Int64"

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    if truncate:
        cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
        conn.commit()
        print(f"Truncated {table}")

    total_rows = 0
    col_list = ", ".join(cols)
    copy_sql = f"COPY {table} ({col_list}) FROM STDIN WITH (FORMAT csv)"

    for chunk in pd.read_csv(csv_path, usecols=cols, dtype=dtype_overrides, chunksize=CHUNK_SIZE):
        chunk = chunk[cols]  # enforce exact column order
        buffer = io.StringIO()
        chunk.to_csv(buffer, index=False, header=False)
        buffer.seek(0)
        cur.copy_expert(copy_sql, buffer)
        conn.commit()
        total_rows += len(chunk)
        print(f"  ... loaded {total_rows} rows into {table}", end="\r")

    print(f"\nDone. Loaded {total_rows} total rows into {table}.")

    cur.execute(f"SELECT COUNT(*) FROM {table};")
    db_count = cur.fetchone()[0]
    print(f"Verification: {table} now has {db_count} rows in Postgres.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, choices=list(TABLE_SPECS.keys()))
    parser.add_argument("--no-truncate", action="store_true",
                         help="Append instead of truncating first (default truncates)")
    args = parser.parse_args()

    load_table(args.table, truncate=not args.no_truncate)
