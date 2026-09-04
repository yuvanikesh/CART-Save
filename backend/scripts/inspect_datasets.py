"""
CartGuard AI — Dataset Inspection Script
Run this from backend/ to get a quick profile of every raw dataset.
Usage: python ../inspect_datasets.py   (or place inside backend/scripts/ and run from there)
"""
import os
import pandas as pd

RAW_DIR = "data/raw"

def inspect_file(path, nrows=50000):
    print("=" * 70)
    print(f"FILE: {path}")
    print("=" * 70)
    try:
        # Read only a sample for huge files (safe for 5GB+ files too)
        df = pd.read_csv(path, nrows=nrows)
    except Exception as e:
        print(f"  Could not read: {e}")
        return

    print(f"Sample shape: {df.shape}  (capped at {nrows} rows for preview)")
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        dtype = df[col].dtype
        n_missing = df[col].isna().sum()
        pct_missing = n_missing / len(df) * 100
        n_unique = df[col].nunique()
        print(f"  - {col:30s} dtype={str(dtype):10s} missing={pct_missing:5.1f}%  unique={n_unique}")

    # Special check: does this look like event-level clickstream data?
    if "event_type" in df.columns:
        print(f"\nevent_type value counts:")
        print(df["event_type"].value_counts())

    if "user_session" in df.columns:
        print(f"\nRows per session (sample): avg {df.groupby('user_session').size().mean():.1f}")

    print()


def main():
    if not os.path.isdir(RAW_DIR):
        print(f"'{RAW_DIR}' not found. Run this script from the backend/ directory.")
        return

    csv_files = []
    for root, _, files in os.walk(RAW_DIR):
        for f in files:
            if f.lower().endswith(".csv"):
                csv_files.append(os.path.join(root, f))

    if not csv_files:
        print("No CSV files found under data/raw/")
        return

    print(f"Found {len(csv_files)} CSV file(s) under {RAW_DIR}/\n")
    for path in csv_files:
        inspect_file(path)


if __name__ == "__main__":
    main()