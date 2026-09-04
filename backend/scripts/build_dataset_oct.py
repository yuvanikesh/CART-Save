"""
CartGuard AI — load_dataset_1: 2019-Oct.csv event->session aggregation
Rolls up event-level clickstream rows into session-level rows matching
the FEATURE_COLUMNS schema used by EnsembleRiskModel.

Usage (from backend/):
    python scripts/build_dataset_oct.py --nrows 500000
    python scripts/build_dataset_oct.py            # full file (can be slow/large)
"""
import argparse
import os
import pandas as pd
import numpy as np


def load_dataset_1(path: str, nrows: int = None) -> pd.DataFrame:
    """
    Load 2019-Oct.csv and aggregate event-level rows into session-level rows.

    KNOWN LIMITATIONS (be upfront about these in your write-up):
    - No payment data at all -> payment_attempts, payment_failures,
      time_on_payment_page, payment_method_switches, form_field_errors
      are ALL zero/NaN for every row from this source. The model trained
      on this alone will lean on browsing/cart behavioral signals, not
      payment signals -> exactly why M2's LLM payment-failure agent should
      rely on synthetic/demo scenarios for that specific diagnosis path.
    - No explicit "checkout step" events -> checkout_steps_completed and
      checkout_time are proxied (see below), not directly observed.
    - No cart-removal event -> cart_removes is always 0 here.
    """
    print(f"Loading {path} (nrows={nrows or 'ALL'})...")
    dtype_map = {
        "event_type": "category",
        "product_id": "int32",
        "category_id": "int64",
        "user_id": "int64",
    }
    df = pd.read_csv(
        path,
        nrows=nrows,
        parse_dates=["event_time"],
        dtype=dtype_map,
    )
    print(f"Loaded {len(df):,} raw events, {df['user_session'].nunique():,} sessions")

    # Sort so within-session ordering is correct for revisit/time calcs
    df = df.sort_values(["user_session", "event_time"])

    sessions = []
    grouped = df.groupby("user_session", sort=False)

    for session_id, g in grouped:
        n_events = len(g)
        views = g[g["event_type"] == "view"]
        carts = g[g["event_type"] == "cart"]
        purchases = g[g["event_type"] == "purchase"]

        session_start = g["event_time"].min()
        session_end = g["event_time"].max()
        session_duration = max((session_end - session_start).total_seconds(), 1.0)

        product_views = len(views)
        cart_adds = len(carts)
        cart_removes = 0  # not observable in this dataset

        # Category switching: count of distinct category_code seen
        category_switches = g["category_code"].dropna().nunique()

        # Page revisits: same product viewed more than once
        page_revisits = int((views["product_id"].value_counts() > 1).sum())

        # Cart value: sum of price for items added to cart (approximation;
        # no quantity field, so this is "value of distinct add-to-cart events")
        cart_value = float(carts["price"].sum()) if len(carts) > 0 else 0.0
        if cart_value == 0.0 and len(views) > 0:
            # fallback: use the most-viewed item's price as a rough proxy
            cart_value = float(views["price"].mean())

        # Tab switches: not observable -> 0
        tab_switches = 0

        # LEAKAGE FIX: checkout_steps_completed and payment_attempts must NOT
        # be derived from `purchases` — that is the same event used to build
        # the `abandoned` label, so a purchase-conditioned proxy makes the
        # feature a deterministic function of the label (AUC collapses to
        # 1.0 on any cart_adds>0 slice). This dataset has no real checkout-
        # funnel or payment events, so both are left fully unobserved (0),
        # matching the other payment_* fields below.
        checkout_steps_completed = 0
        checkout_time = 0.0  # not observable, left as 0

        # Label: did this session convert?
        converted = len(purchases) > 0
        abandoned = int(not converted)

        sessions.append({
            "session_id": session_id,
            "user_id": g["user_id"].iloc[0],
            "session_duration": session_duration,
            "product_views": product_views,
            "cart_adds": cart_adds,
            "cart_removes": cart_removes,
            "cart_changes": cart_adds + cart_removes,
            "cart_value": cart_value,
            "category_switches": category_switches,
            "tab_switches": tab_switches,
            "page_revisits": page_revisits,
            "checkout_steps_completed": checkout_steps_completed,
            "checkout_time": checkout_time,
            # Payment fields: unobservable in this dataset -> zero-filled
            "payment_attempts": 0,
            "payment_failures": 0,
            "time_on_payment_page": 0.0,
            "payment_method_switches": 0,
            "form_field_errors": 0,
            "back_navigations": 0,
            "session_recency_minutes": 0.0,
            "abandoned": abandoned,
            "source_dataset": "2019-Oct",
        })

    session_df = pd.DataFrame(sessions)

    # is_returning_visitor: has this user_id appeared in an earlier session?
    session_df = session_df.sort_values("user_id")
    seen = set()
    is_returning = []
    for uid in session_df["user_id"]:
        is_returning.append(1 if uid in seen else 0)
        seen.add(uid)
    session_df["is_returning_visitor"] = is_returning

    print(f"Built {len(session_df):,} session-level rows")
    print(f"Abandonment rate: {session_df['abandoned'].mean():.2%}")
    print(f"Sessions with cart_adds > 0: {(session_df['cart_adds'] > 0).sum():,} "
          f"({(session_df['cart_adds'] > 0).mean():.1%})")

    return session_df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nrows", type=int, default=500000,
                         help="Number of raw event rows to read (omit flag / pass 0 for full file)")
    parser.add_argument("--input", default="data/raw/2019-Oct.csv")
    parser.add_argument("--output", default="data/processed/dataset1_clean.parquet")
    args = parser.parse_args()

    nrows = None if not args.nrows else args.nrows
    df = load_dataset_1(args.input, nrows=nrows)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    df.to_parquet(args.output, index=False)
    print(f"\nSaved to {args.output}")
    print(f"\nColumn dtypes:\n{df.dtypes}")


if __name__ == "__main__":
    main()