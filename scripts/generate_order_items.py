"""
Phase 2, Step 4: generate the order_items table.

Reads order_ids from orders.csv and product_id/price from products.csv.
Each order gets 1-8 line items (not a flat multiplier), generated until
the target row count is reached.

No deliberate quality issues injected here directly -- order_items
inherits messiness from upstream (orders' negative amounts, products'
duplicate product_ids) rather than introducing new problems, which
mirrors how data quality issues actually propagate downstream in
real pipelines.
"""
import argparse
import random

import pandas as pd

random.seed(42)

MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 8


def generate_order_items(target_rows: int, order_ids: list[int], products_df: pd.DataFrame) -> pd.DataFrame:
    product_records = products_df[["product_id", "price"]].to_dict("records")

    rows = []
    order_item_id = 1
    order_idx = 0
    n_orders = len(order_ids)

    while len(rows) < target_rows:
        order_id = order_ids[order_idx % n_orders]
        order_idx += 1

        n_items = random.randint(MIN_ITEMS_PER_ORDER, MAX_ITEMS_PER_ORDER)
        for _ in range(n_items):
            if len(rows) >= target_rows:
                break
            product = random.choice(product_records)
            quantity = random.randint(1, 5)
            unit_price = product["price"]

            rows.append(
                {
                    "order_item_id": order_item_id,
                    "order_id": order_id,
                    "product_id": product["product_id"],
                    "quantity": quantity,
                    "unit_price": unit_price,
                }
            )
            order_item_id += 1

    df = pd.DataFrame(rows)
    df["line_total"] = (df["quantity"] * df["unit_price"]).round(2)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=2000, help="Target number of order_items to generate")
    args = parser.parse_args()

    orders_df = pd.read_csv("data/generated/orders.csv", usecols=["order_id"])
    order_ids = orders_df["order_id"].tolist()

    products_df = pd.read_csv("data/generated/products.csv", usecols=["product_id", "price"])

    df = generate_order_items(args.rows, order_ids, products_df)

    out_path = "data/generated/order_items.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"  Distinct orders covered: {df['order_id'].nunique()} / {len(order_ids)}")
    print(f"  Avg items per order touched: {len(df) / df['order_id'].nunique():.2f}")
