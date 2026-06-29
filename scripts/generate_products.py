"""
Phase 2, Step 2: generate the products table.

Produces data/generated/products.csv matching the schema in
scripts/init_oltp_schema.sql, with deliberately injected issues:
  - some null categories
  - some duplicate product_ids (simulates a duplicate-SKU bug)
"""
import argparse
import random

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

CATEGORIES = [
    "Electronics", "Apparel", "Home & Kitchen", "Beauty", "Sports",
    "Toys", "Books", "Grocery", "Automotive", "Office Supplies",
]
BRANDS = [fake.company() for _ in range(200)]  # fixed brand pool, reused across products

PCT_NULL_CATEGORY = 0.02
PCT_DUPLICATE_PRODUCT_NAME = 0.01


def generate_products(n_rows: int) -> pd.DataFrame:
    rows = []
    for product_id in range(1, n_rows + 1):
        cost = round(random.uniform(2, 300), 2)
        price = round(cost * random.uniform(1.2, 2.5), 2)  # price always above cost
        rows.append(
            {
                "product_id": product_id,
                "product_name": fake.unique.catch_phrase(),
                "category": random.choice(CATEGORIES),
                "brand": random.choice(BRANDS),
                "price": price,
                "cost": cost,
                "updated_at": fake.date_time_between(start_date="-2y", end_date="now"),
            }
        )

    df = pd.DataFrame(rows)

    # --- Inject: null categories ---
    n_null_cat = int(n_rows * PCT_NULL_CATEGORY)
    null_idx = df.sample(n=n_null_cat, random_state=1).index
    df.loc[null_idx, "category"] = None

    # --- Inject: duplicate product_names (two different product_ids, same name -- a realistic vendor data-entry duplicate) ---
    n_dupes = int(n_rows * PCT_DUPLICATE_PRODUCT_NAME)
    dupe_targets = df.sample(n=n_dupes, random_state=2).index
    dupe_source_names = df.sample(n=n_dupes, random_state=3)["product_name"].values
    df.loc[dupe_targets, "product_name"] = dupe_source_names

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1000, help="Number of products to generate")
    args = parser.parse_args()

    df = generate_products(args.rows)

    out_path = "data/generated/products.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"  Null categories: {df['category'].isna().sum()}")
    print(f"  Duplicate product_names: {df['product_name'].duplicated().sum()}")
