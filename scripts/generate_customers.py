"""
Phase 2, Step 1: generate the customers table.

Produces a CSV at data/generated/customers.csv matching the schema
in scripts/init_oltp_schema.sql exactly, with deliberately injected
data quality issues:
  - some missing emails
  - some duplicate emails
  - some invalid phone numbers

Run with a small --rows value first to sanity check the output,
then re-run with the full volume (100,000) once it looks right.
"""
import argparse
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

LOYALTY_TIERS = ["bronze", "silver", "gold", "platinum"]

# Fraction of rows that get each deliberate quality issue
PCT_MISSING_EMAIL = 0.02
PCT_DUPLICATE_EMAIL = 0.01
PCT_INVALID_PHONE = 0.02


def generate_customers(n_rows: int) -> pd.DataFrame:
    rows = []
    seen_emails = []

    for customer_id in range(1, n_rows + 1):
        name = fake.name()
        email = fake.unique.email()
        phone = fake.phone_number()
        signup_date = fake.date_between(start_date="-3y", end_date="today")
        updated_at = datetime.combine(signup_date, datetime.min.time()) + timedelta(
            days=random.randint(0, 60)
        )

        rows.append(
            {
                "customer_id": customer_id,
                "name": name,
                "email": email,
                "phone": phone,
                "city": fake.city(),
                "state": fake.state_abbr(),
                "country": "USA",
                "signup_date": signup_date,
                "loyalty_tier": random.choice(LOYALTY_TIERS),
                "updated_at": updated_at,
            }
        )
        seen_emails.append(email)

    df = pd.DataFrame(rows)

    # --- Inject: missing emails ---
    n_missing = int(n_rows * PCT_MISSING_EMAIL)
    missing_idx = df.sample(n=n_missing, random_state=1).index
    df.loc[missing_idx, "email"] = None

    # --- Inject: duplicate emails (copy an existing email onto another row) ---
    n_dupes = int(n_rows * PCT_DUPLICATE_EMAIL)
    dupe_targets = df.sample(n=n_dupes, random_state=2).index
    dupe_sources = df.sample(n=n_dupes, random_state=3)["email"].values
    df.loc[dupe_targets, "email"] = dupe_sources

    # --- Inject: invalid phone numbers (garbage strings) ---
    n_bad_phone = int(n_rows * PCT_INVALID_PHONE)
    bad_phone_idx = df.sample(n=n_bad_phone, random_state=4).index
    df.loc[bad_phone_idx, "phone"] = "INVALID-000"

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=1000, help="Number of customers to generate")
    args = parser.parse_args()

    df = generate_customers(args.rows)

    out_path = "data/generated/customers.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"  Missing emails: {df['email'].isna().sum()}")
    print(f"  Duplicate emails: {df['email'].duplicated().sum()}")
    print(f"  Invalid phones: {(df['phone'] == 'INVALID-000').sum()}")
