"""EDA on crypto_data.csv -> figures in ./figures + summary printed to stdout.

    python3 analyze.py [path/to/crypto_data.csv]
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")
HERE = os.path.dirname(os.path.abspath(__file__))
FIGS = os.path.join(HERE, "figures")

NUM = ["current_price", "market_cap", "market_cap_rank", "total_volume",
       "high_24h", "low_24h", "price_change_24h",
       "price_change_percentage_24h", "circulating_supply"]


class CryptoEDA:
    def __init__(self, csv_path):
        self.path = csv_path
        os.makedirs(FIGS, exist_ok=True)
        self.df = self._load()

    # ---------- data ----------
    def _load(self):
        df = pd.read_csv(self.path, parse_dates=["timestamp"])
        for c in NUM:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.drop_duplicates(subset=["timestamp", "symbol"])
        # engineered features
        df["intraday_range_pct"] = (df.high_24h - df.low_24h) / df.low_24h * 100
        df["volume_to_mcap"] = df.total_volume / df.market_cap
        df["log_market_cap"] = np.log10(df.market_cap.replace(0, np.nan))
        df["log_volume"] = np.log10(df.total_volume.replace(0, np.nan))
        return df

    def _save(self, name):
        plt.tight_layout()
        plt.savefig(os.path.join(FIGS, name), dpi=140)
        plt.close()
        print("  figures/" + name)

    def summary(self):
        d = self.df
        print(f"rows={len(d)}  coins={d.symbol.nunique()}  "
              f"snapshots={d.timestamp.nunique()}")
        print(f"window: {d.timestamp.min()} -> {d.timestamp.max()}\n")
        print(d[NUM].describe().T.to_string(float_format=lambda x: f"{x:,.4f}"))
        print("\nmissing values:\n", d[NUM].isna().sum().to_string(), "\n")

    # ---------- univariate ----------
    def univariate(self):
        d = self.df
        fig, ax = plt.subplots(1, 2, figsize=(12, 4))
        sns.histplot(d.current_price.dropna(), bins=60, ax=ax[0], color="#3b6ea5")
        ax[0].set(title="current_price (raw)", xlabel="USD")
        sns.histplot(np.log10(d.current_price.replace(0, np.nan).dropna()),
                     bins=60, ax=ax[1], color="#3b6ea5")
        ax[1].set(title="current_price (log10) — heavy right skew",
                  xlabel="log10 USD")
        self._save("uni_price_hist.png")

        plt.figure(figsize=(10, 3.2))
        sns.boxplot(x=d.log_market_cap.dropna(), color="#e0a458")
        plt.title("market_cap (log10 USD) — box plot")
        self._save("uni_marketcap_box.png")

        fig, ax = plt.subplots(1, 2, figsize=(12, 4))
        sns.histplot(d.log_volume.dropna(), bins=50, ax=ax[0], color="#5b8c5a")
        ax[0].set(title="total_volume (log10 USD)")
        sns.histplot(d.price_change_percentage_24h.dropna(), bins=60,
                     ax=ax[1], color="#a4586a")
        ax[1].axvline(0, color="k", lw=1, ls="--")
        ax[1].set(title="24h % change distribution", xlabel="%")
        self._save("uni_volume_pct.png")

    # ---------- bivariate ----------
    def bivariate(self):
        d = self.df
        latest = d[d.timestamp == d.timestamp.max()]

        plt.figure(figsize=(6.5, 5))
        sns.scatterplot(data=latest, x="market_cap", y="total_volume",
                        hue="price_change_percentage_24h", palette="coolwarm",
                        s=55, edgecolor="k", linewidth=.3)
        plt.xscale("log"); plt.yscale("log")
        r = np.corrcoef(latest.log_market_cap.dropna(),
                        latest.log_volume.dropna())[0, 1]
        plt.title(f"market_cap vs total_volume (log-log), r={r:.2f}")
        self._save("bi_mcap_vs_volume.png")

        plt.figure(figsize=(6.5, 5))
        sns.scatterplot(data=latest, x="current_price",
                        y="price_change_percentage_24h", s=45,
                        color="#3b6ea5", edgecolor="k", linewidth=.3)
        plt.xscale("symlog")
        plt.axhline(0, color="k", lw=1, ls="--")
        plt.title("current_price vs 24h % change")
        self._save("bi_price_vs_pctchange.png")

        plt.figure(figsize=(6, 5.5))
        sns.scatterplot(data=latest, x="low_24h", y="high_24h", s=45,
                        color="#5b8c5a", edgecolor="k", linewidth=.3)
        lims = [latest.low_24h.min(), latest.high_24h.max()]
        plt.plot(lims, lims, "r--", lw=1, label="y = x")
        plt.xscale("log"); plt.yscale("log"); plt.legend()
        plt.title("high_24h vs low_24h")
        self._save("bi_high_vs_low.png")

        # time series of the top 5 by market cap
        top5 = latest.nlargest(5, "market_cap").symbol.tolist()
        piv = (d[d.symbol.isin(top5)]
               .pivot_table(index="timestamp", columns="symbol",
                            values="current_price"))
        norm = piv / piv.iloc[0] * 100
        plt.figure(figsize=(10, 4.5))
        for c in norm.columns:
            plt.plot(norm.index, norm[c], label=c, lw=1.6)
        plt.legend(ncol=5); plt.ylabel("indexed to 100")
        plt.title("Top-5 price paths over the collection window")
        self._save("ts_top5_indexed.png")

    # ---------- multivariate ----------
    def multivariate(self):
        d = self.df
        latest = d[d.timestamp == d.timestamp.max()]
        cols = ["current_price", "market_cap", "total_volume", "high_24h",
                "low_24h", "price_change_24h", "price_change_percentage_24h",
                "circulating_supply", "intraday_range_pct", "volume_to_mcap"]

        plt.figure(figsize=(9, 7.5))
        corr = d[cols].corr(method="spearman")
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                    square=True, cbar_kws={"shrink": .8},
                    annot_kws={"size": 7})
        plt.title("Spearman correlation heatmap")
        self._save("multi_corr_heatmap.png")

        pair_cols = ["log_market_cap", "log_volume",
                     "price_change_percentage_24h", "intraday_range_pct"]
        g = sns.pairplot(latest[pair_cols].dropna(), corner=True,
                         plot_kws=dict(s=22, edgecolor="k", linewidth=.2),
                         diag_kind="kde")
        g.figure.suptitle("Pair plot (latest snapshot)", y=1.01)
        g.figure.savefig(os.path.join(FIGS, "multi_pairplot.png"), dpi=140,
                         bbox_inches="tight")
        plt.close("all")
        print("  figures/multi_pairplot.png")

        # volatility leaderboard
        vol = (d.groupby("symbol").price_change_percentage_24h
               .std().dropna().nlargest(15))
        plt.figure(figsize=(8, 5))
        sns.barplot(x=vol.values, y=vol.index, color="#a4586a")
        plt.xlabel("std of 24h % change"); plt.ylabel("")
        plt.title("Most volatile coins over the window")
        self._save("multi_volatility_rank.png")

    def run(self):
        self.summary()
        print("figures written:")
        self.univariate()
        self.bivariate()
        self.multivariate()


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data", "crypto_data.csv")
    CryptoEDA(path).run()
