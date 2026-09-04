"""Hourly collector: top 100 coins from CoinGecko -> append to data/crypto_data.csv

Run locally:      python3 collect.py
In CI:            invoked hourly by .github/workflows/collect.yml
"""
import csv
import os
import sys
import time
from datetime import datetime, timezone

import requests

URL = "https://api.coingecko.com/api/v3/coins/markets"
PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 100,
    "page": 1,
    "sparkline": "false",
    "price_change_percentage": "24h",
}

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "crypto_data.csv")

FIELDS = [
    "timestamp", "name", "symbol", "current_price", "market_cap",
    "market_cap_rank", "total_volume", "high_24h", "low_24h",
    "price_change_24h", "price_change_percentage_24h", "circulating_supply",
]


def fetch(retries=4, backoff=15):
    """GET with retry. CoinGecko's free tier 429s readily; back off and retry."""
    headers = {"accept": "application/json"}
    key = os.environ.get("COINGECKO_API_KEY")
    if key:
        headers["x-cg-demo-api-key"] = key

    last = None
    for attempt in range(retries):
        try:
            r = requests.get(URL, params=PARAMS, timeout=30, headers=headers)
            if r.status_code == 429:
                wait = backoff * (attempt + 1)
                print(f"429 rate limited, sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                raise ValueError(f"unexpected payload: {str(data)[:200]}")
            return data
        except (requests.RequestException, ValueError) as e:
            last = e
            print(f"attempt {attempt+1}/{retries} failed: {e}", file=sys.stderr)
            time.sleep(backoff * (attempt + 1))
    raise SystemExit(f"all retries failed: {last}")


def main():
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    coins = fetch()

    rows = [{
        "timestamp": ts,
        "name": c.get("name"),
        "symbol": (c.get("symbol") or "").upper(),
        "current_price": c.get("current_price"),
        "market_cap": c.get("market_cap"),
        "market_cap_rank": c.get("market_cap_rank"),
        "total_volume": c.get("total_volume"),
        "high_24h": c.get("high_24h"),
        "low_24h": c.get("low_24h"),
        "price_change_24h": c.get("price_change_24h"),
        "price_change_percentage_24h": c.get("price_change_percentage_24h"),
        "circulating_supply": c.get("circulating_supply"),
    } for c in coins]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    new_file = not os.path.exists(OUT) or os.path.getsize(OUT) == 0
    with open(OUT, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)

    print(f"{ts}: wrote {len(rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
