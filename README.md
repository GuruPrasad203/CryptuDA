# Real-Time Cryptocurrency Market Analysis

Hourly snapshots of the top 100 cryptocurrencies by market cap (CoinGecko),
collected for 7 days, then analysed.

**Target dataset:** 100 coins × 24 hours × 7 days = **16,800 records**

## Layout

```
collect.py                      hourly snapshot -> data/crypto_data.csv
analyze.py                      full EDA -> figures/
status.py                       collection health: coverage, gaps, ETA
data/crypto_data.csv            the dataset (committed hourly by CI)
.github/workflows/collect.yml   hourly schedule
```

## Setup

1. Create a **public** GitHub repo and push this directory.
2. Actions tab → enable workflows if prompted.
3. Actions → *Collect crypto snapshot* → **Run workflow** to verify.
   A commit named `snapshot <timestamp>` should appear within a minute.

That's it — it now runs every hour on its own.

### Optional: CoinGecko demo API key

Free at <https://www.coingecko.com/en/api/pricing>. Raises the rate limit and
makes 429s much less likely. Add it under
Settings → Secrets and variables → Actions → New repository secret,
named `COINGECKO_API_KEY`. The workflow picks it up automatically; it works
fine without one.

## Collecting

Check progress any time:

```bash
git pull
pip install -r requirements.txt
python status.py
```

Reports rows, snapshot count, coverage %, missing-hour runs, partial
snapshots, and coin churn.

## Analysing

After ~7 days:

```bash
git pull
python analyze.py
```

Writes 10 figures to `figures/`:

| Level | Figures |
|---|---|
| Univariate | price histogram (raw + log10), market_cap boxplot, volume histogram, 24h % change distribution |
| Bivariate | market_cap vs total_volume, current_price vs 24h % change, high_24h vs low_24h, top-5 indexed price paths |
| Multivariate | Spearman correlation heatmap, pair plot, volatility leaderboard |

## Notes on the data

- **Timestamps are UTC.** Convert to IST (+5:30) before discussing
  time-of-day effects.
- **Log-scale everything.** Market caps span ~6 orders of magnitude; raw
  histograms are unreadable.
- **Spearman, not Pearson,** for correlations — relationships are monotonic
  but not linear, and BTC/ETH dominate Pearson as outliers.
- **`high_24h` vs `low_24h` correlate at r≈0.999** and say nothing on their
  own. `intraday_range_pct = (high-low)/low` is the useful derived form.
- **The 24h window is rolling**, so consecutive hourly `price_change_24h`
  values overlap and are strongly autocorrelated. Fine for descriptive EDA;
  do not treat the 16,800 rows as independent in any hypothesis test.
- **Top-100 membership changes** during the week — coins enter and leave the
  ranking, so the panel is unbalanced. `status.py` reports the churn count.

## Engineered features (added in `analyze.py`)

| Feature | Definition | Use |
|---|---|---|
| `intraday_range_pct` | `(high_24h - low_24h) / low_24h * 100` | volatility proxy |
| `volume_to_mcap` | `total_volume / market_cap` | liquidity / turnover |
| `log_market_cap`, `log_volume` | `log10(x)` | tames the skew |
