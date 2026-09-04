"""
CartGuard AI — Deeper check on ambiguous datasets
Run from backend/: python scripts/inspect_ambiguous.py
"""
import pandas as pd

print("=" * 70)
print("ecommerce_clickstream_transactions.csv — deeper look")
print("=" * 70)
df3 = pd.read_csv("data/raw/ecommerce_clickstream_transactions.csv")
print(f"Full shape: {df3.shape}")
print(f"\nEventType value counts:\n{df3['EventType'].value_counts()}")
print(f"\nOutcome value counts:\n{df3['Outcome'].value_counts(dropna=False)}")
print(f"\nUnique SessionIDs: {df3['SessionID'].nunique()}")
print(f"Rows per SessionID:\n{df3.groupby('SessionID').size()}")
print(f"\nSample rows:\n{df3.head(10)}")

print("\n" + "=" * 70)
print("clicks_missing.csv — full look (small file)")
print("=" * 70)
df4 = pd.read_csv("data/raw/clicks_missing.csv")
print(f"Full shape: {df4.shape}")
print(f"\nSample rows:\n{df4.head(10)}")
print(f"\nlocation value counts:\n{df4['location'].value_counts()}")

print("\n" + "=" * 70)
print("Overlap check: 2019-Oct.csv user_id vs customers.csv customer_id")
print("=" * 70)
oct_df = pd.read_csv("data/raw/2019-Oct.csv", usecols=["user_id"])
cust_df = pd.read_csv("data/raw/customers.csv", usecols=["customer_id"])
oct_ids = set(oct_df["user_id"].unique())
cust_ids = set(cust_df["customer_id"].unique())
overlap = oct_ids & cust_ids
print(f"Unique user_id in 2019-Oct.csv sample: {len(oct_ids)}")
print(f"Unique customer_id in customers.csv: {len(cust_ids)}")
print(f"Overlap: {len(overlap)} ({len(overlap)/max(len(oct_ids),1)*100:.1f}% of Oct users)")