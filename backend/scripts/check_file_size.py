"""
Quick file size + row count check — reads in chunks so it won't blow up
memory even if the file turns out to be huge.
Usage: python scripts/check_file_size.py
"""
import os

path = "data/raw/2019-Oct.csv"

size_bytes = os.path.getsize(path)
size_mb = size_bytes / (1024 * 1024)
print(f"File size: {size_mb:.2f} MB ({size_bytes:,} bytes)")

# Count lines without loading whole file into memory
count = 0
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    for _ in f:
        count += 1

print(f"Total lines (including header): {count:,}")
print(f"Total data rows: {count - 1:,}")