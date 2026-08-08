"""
Market correlation signal -- part two of the two-part regime
detector (breadth + correlation). Answers: how tightly are assets
moving together right now, as a genuine structural signal rather
than a scalar percentile.

Uses simple rolling pairwise correlation across the core equity
universe (not the full 1,368 -- computing a full correlation
matrix across 1,368 assets every week would be a real, different
computational cost than the trivial per-ticker scoring checked
earlier tonight, worth using a representative core set instead).
"""
import os
import pandas as pd
import numpy as np
import json

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

# Representative core set -- major, liquid, sector-diverse tickers
# already validated throughout this session, not the full 1,368.
# Real correlation structure across a diverse core set should be
# a meaningful, honest signal without the computational cost of
# a full 1,368x1,368 matrix every week.
CORE_SET = ["VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF", "XLE", "XLK",
            "XLI", "XLB", "XLU", "IWM", "SOXX", "GDX"]


def compute_correlation(px, date, universe=None, lookback=63):
    """
    Average pairwise correlation across the core set's trailing
    returns as of `date`. Higher = more correlated = more
    "everything moving together" (a real, distinct signal from
    breadth's "how many are declining").
    """
    if universe is None:
        universe = CORE_SET

    avail = [t for t in universe if t in px.columns]
    hist = px.loc[:date, avail].dropna(axis=1, thresh=lookback)
    if len(hist.columns) < 4:
        return None

    rets = hist.pct_change().dropna().iloc[-lookback:]
    if len(rets) < 20:
        return None

    corr_matrix = rets.corr()
    n = len(corr_matrix)
    # Average of the off-diagonal (pairwise) correlations only
    off_diag_sum = corr_matrix.values.sum() - n  # subtract the n 1.0s on diagonal
    n_pairs = n * (n - 1)
    avg_corr = off_diag_sum / n_pairs if n_pairs > 0 else None

    return {"avg_correlation": float(avg_corr), "n_assets": n}


def validate_correlation_separation(px, verbose=True):
    """Same real stressed-vs-calm validation method as breadth."""
    STRESSED_DATES = [
        ("2008-11-15", "2008 crisis depth"),
        ("2009-02-27", "2008-09 crisis trough"),
        ("2020-03-20", "COVID crash depth"),
        ("2022-06-15", "2022 rate crisis"),
    ]
    CALM_DATES = [
        ("2005-06-15", "calm mid-2000s"),
        ("2013-06-15", "calm mid-2013"),
        ("2017-06-15", "calm mid-2017"),
        ("2021-06-15", "calm mid-2021"),
    ]

    print("=== STRESSED DATES ===")
    stressed_corrs = []
    for date_str, label in STRESSED_DATES:
        d = pd.Timestamp(date_str)
        result = compute_correlation(px, d)
        if result:
            print(f"  {date_str} ({label}): avg_corr={result['avg_correlation']:.3f} "
                  f"n={result['n_assets']}")
            stressed_corrs.append(result['avg_correlation'])

    print()
    print("=== CALM DATES ===")
    calm_corrs = []
    for date_str, label in CALM_DATES:
        d = pd.Timestamp(date_str)
        result = compute_correlation(px, d)
        if result:
            print(f"  {date_str} ({label}): avg_corr={result['avg_correlation']:.3f} "
                  f"n={result['n_assets']}")
            calm_corrs.append(result['avg_correlation'])

    print()
    if stressed_corrs and calm_corrs:
        s_mean = np.mean(stressed_corrs)
        c_mean = np.mean(calm_corrs)
        print(f"Stressed avg correlation: {s_mean:.3f}")
        print(f"Calm avg correlation:     {c_mean:.3f}")
        print(f"Separation: {s_mean - c_mean:+.3f}")


if __name__ == "__main__":
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)
    validate_correlation_separation(px)
