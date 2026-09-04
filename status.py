"""Collection health check: coverage, gaps, ETA to target.

    python3 status.py [path/to/crypto_data.csv]
"""
import os
import sys
from datetime import timedelta

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET_HOURS = 168          # 7 days
EXPECTED_PER_SNAPSHOT = 100


def main(path):
    if not os.path.exists(path):
        raise SystemExit(f"no data yet at {path}")

    df = pd.read_csv(path, parse_dates=["timestamp"])
    snaps = df.timestamp.drop_duplicates().sort_values()
    first, last = snaps.iloc[0], snaps.iloc[-1]
    elapsed = int((last - first) / timedelta(hours=1)) + 1

    print(f"rows          : {len(df):,}")
    print(f"snapshots     : {len(snaps)}  (target {TARGET_HOURS})")
    print(f"first         : {first}")
    print(f"last          : {last}")
    print(f"elapsed hours : {elapsed}")
    print(f"coverage      : {len(snaps)/elapsed*100:5.1f}% of hours elapsed")
    print(f"progress      : {len(snaps)/TARGET_HOURS*100:5.1f}% of 7-day target")

    # missing hours
    full = pd.date_range(first.floor("h"), last.floor("h"), freq="h", tz=first.tz)
    have = set(snaps.dt.floor("h"))
    missing = [t for t in full if t not in have]
    print(f"missed hours  : {len(missing)}")
    if missing:
        # collapse into runs
        runs, start, prev = [], missing[0], missing[0]
        for t in missing[1:]:
            if (t - prev) == timedelta(hours=1):
                prev = t
                continue
            runs.append((start, prev)); start = prev = t
        runs.append((start, prev))
        print("  gaps:")
        for a, b in runs[:15]:
            n = int((b - a) / timedelta(hours=1)) + 1
            print(f"    {a:%Y-%m-%d %H:%M} .. {b:%Y-%m-%d %H:%M}  ({n}h)")
        if len(runs) > 15:
            print(f"    ... and {len(runs)-15} more gaps")

    # short snapshots (partial API responses)
    counts = df.groupby("timestamp").size()
    short = counts[counts != EXPECTED_PER_SNAPSHOT]
    if len(short):
        print(f"\npartial snapshots ({len(short)}):")
        print(short.head(10).to_string())

    # coin churn — top-100 membership changes over the window
    per = df.groupby("timestamp").symbol.apply(set)
    churn = sum(len(per.iloc[i] ^ per.iloc[i - 1]) for i in range(1, len(per)))
    print(f"\ncoin churn    : {churn} membership changes "
          f"({df.symbol.nunique()} distinct symbols seen)")

    remaining = TARGET_HOURS - len(snaps)
    if remaining > 0:
        print(f"\n~{remaining}h of collection remaining "
              f"({remaining/24:.1f} days at full coverage)")
    else:
        print("\ntarget reached — run analyze.py")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data", "crypto_data.csv"))
