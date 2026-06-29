"""
Phase 2, Step 5: generate the payments table.

One payment per order (1:1 here, unlike order_items), with amount
normally matching the order's order_amount.

Injected issues:
  - late-arriving payments (payment_date well after order_date --
    handled implicitly since we just generate independently-random
    payment dates relative to order_date, some intentionally delayed)
  - a small percentage of mismatched amounts (payment != order_amount)
  - a small percentage of failed/pending payment_status
"""
import argparse
import random
from datetime import timedelta

import pandas as pd

random.seed(42)

PAYMENT_STATUSES_WEIGHTED = (
    ["completed"] * 90 + ["failed"] * 5 + ["pending"] * 3 + ["refunded"] * 2
)
PCT_AMOUNT_MISMATCH = 0.015
PCT_LATE_PAYMENT = 0.03  # payment_date 5-30 days after order_date instead of same-day


def generate_payments(orders_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for payment_id, order in enumerate(orders_df.itertuples(index=False), start=1):
        order_date = pd.to_datetime(order.order_date)
        # Most payments happen within 0-2 days of the order
        delay_days = random.randint(0, 2)
        payment_date = order_date + timedelta(days=delay_days, hours=random.randint(0, 23))

        rows.append(
            {
                "payment_id": payment_id,
                "order_id": order.order_id,
                "payment_date": payment_date,
                "payment_status": random.choice(PAYMENT_STATUSES_WEIGHTED),
                "amount": order.order_amount,
            }
        )

    df = pd.DataFrame(rows)

    # --- Inject: late-arriving payments ---
    n_late = int(len(df) * PCT_LATE_PAYMENT)
    late_idx = df.sample(n=n_late, random_state=1).index
    df.loc[late_idx, "payment_date"] = df.loc[late_idx, "payment_date"] + pd.to_timedelta(
        [random.randint(5, 30) for _ in range(n_late)], unit="D"
    )

    # --- Inject: amount mismatches (payment doesn't match order_amount) ---
    n_mismatch = int(len(df) * PCT_AMOUNT_MISMATCH)
    mismatch_idx = df.sample(n=n_mismatch, random_state=2).index
    df.loc[mismatch_idx, "amount"] = (
        df.loc[mismatch_idx, "amount"] * random.uniform(0.5, 0.9)
    ).round(2)

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rows", type=int, default=None,
        help="Optional cap on number of payments (defaults to one per order)"
    )
    args = parser.parse_args()

    orders_df = pd.read_csv(
        "data/generated/orders.csv",
        usecols=["order_id", "order_date", "order_amount"],
    )
    if args.rows:
        orders_df = orders_df.head(args.rows)

    df = generate_payments(orders_df)

    out_path = "data/generated/payments.csv"
    df.to_csv(out_path, index=False)

    print(f"Wrote {len(df)} rows to {out_path}")
    print(f"  Status breakdown:\n{df['payment_status'].value_counts()}")
    mismatches = (df["amount"] != orders_df.set_index('order_id').loc[df['order_id'], 'order_amount'].values).sum()
    print(f"  Amount mismatches vs order_amount: {mismatches}")
