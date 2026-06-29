"""
Phase 2, Step 6: generate the campaigns table.

Small reference table, no foreign keys, no injected quality issues --
campaigns are the "clean" dimension; messiness shows up later in
campaign_events (Phase 6, streaming).
"""
import argparse
import random
from datetime import timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

CHANNELS = ["email", "social_media", "search_ads", "display_ads", "affiliate", "sms"]


def generate_campaigns(n_rows: int) -> pd.DataFrame:
    rows = []
    for campaign_id in range(1, n_rows + 1):
        start_date = fake.date_between(start_date="-2y", end_date="+30d")
        duration_days = random.randint(7, 90)
        end_date = start_date + timedelta(days=duration_days)

        rows.append(
            {
                "campaign_id": campaign_id,
                "campaign_name": f"{fake.bs().title()} Campaign",
                "channel": random.choice(CHANNELS),
                "budget": round(random.uniform(500, 50000), 2),
                "start_date": start_date,
                "end_date": end_date,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=5000, help="Number of campaigns to generate")
    args = parser.parse_args()

    df = generate_campaigns(args.rows)

    out_path = "data/generated/campaigns.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"  Channel breakdown:\n{df['channel'].value_counts()}")
