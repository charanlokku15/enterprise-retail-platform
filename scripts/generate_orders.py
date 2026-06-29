"""
Phase 2, Step 3: generate the orders table.

Reads existing customer_ids from data/generated/customers.csv so every
order references a real (or deliberately NULL) customer.

Injected issues:
  - negative order_amount
  - missing customer_id (NULL -- valid at the DB level, a real quality issue
    at the analytics level)
  - invalid order_status (garbage value not in the real status set)
"""
import argparse
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

REAL_STATUSES = ["pending", "shipped", "delivered", "cancelled", "returned"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "gift_card", "bank_transfer"]

PCT_NEGATIVE_AMOUNT = 0.01
PCT_MISSING_CUSTOMER = 0.015
PCT_INVALID_STATUS = 0.01


def generate_orders(n_rows: int, customer_ids: list[int]) -> pd.DataFrame:
    rows = []
    start = datetime(2023, 1, 1)
    end = datetime(2026, 6, 29)

    for order_id in range(1, n_rows + 1):
        order_date = fake.date_time_between(start_date=start, end_date=end)
        amount = round(random.uniform(10, 500), 2)
        rows.append(
            {
                "order_id": order_id,
                "customer_id": random.choice(customer_ids),
                "order_date": order_date,
                "order_status": random.choice(REAL_STATUSES),
                "order_amount": amount,
                "payment_method": random.choice(PAYMENT_METHODS),
            }
        )

    df = pd.DataFrame(rows)

    # --- Inject: negative order amounts ---
    n_neg = int(n_rows * PCT_NEGATIVE_AMOUNT)
    neg_idx = df.sample(n=n_neg, random_state=1).index
    df.loc[neg_idx, "order_amount"] = -df.loc[neg_idx, "order_amount"]

    # --- Inject: missing customer_id (NULL -- allowed by the FK, still a quality issue) ---
    n_missing_cust = int(n_rows * PCT_MISSING_CUSTOMER)
    missing_idx = df.sample(n=n_missing_cust, random_state=2).index
    df.loc[missing_idx, "customer_id"] = None

    # --- Inject: invalid order_status ---
    n_bad_status = int(n_rows * PCT_INVALID_STATUS)
    bad_status_idx = df.sample(n=n_bad_status, random_state=3).index
    df.loc[bad_status_idx, "order_status"] = "UNKNOWN_STATUS"

    df["customer_id"] = df["customer_id"].astype("Int64")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1000, help="Number of orders to generate")
    args = parser.parse_args()

    customers_df = pd.read_csv("data/generated/customers.csv", usecols=["customer_id"])
    customer_ids = customers_df["customer_id"].tolist()

    df = generate_orders(args.rows, customer_ids)

    out_path = "data/generated/orders.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"  Negative amounts: {(df['order_amount'] < 0).sum()}")
    print(f"  Missing customer_id: {df['customer_id'].isna().sum()}")
    print(f"  Invalid statuses: {(df['order_status'] == 'UNKNOWN_STATUS').sum()}")
