"""
Market breadth signal -- part one of the two-part regime detector
(breadth + correlation). Answers: how many assets in the real,
validated universe are actually declining right now, and how
badly, rather than compressing everything into a single scalar
percentile the way the existing dial does.

Built and validated in isolation before combining with a
correlation signal, same discipline as every dial this session.
"""
import os
import pandas as pd
import numpy as np
import json

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")


def compute_breadth(px, date, universe, ma_window=200):
    """
    For each ticker in universe, check whether its price is above
    or below its own trailing moving average as of `date`.

    Returns:
      pct_above: fraction of tickers currently above their MA
      pct_below: fraction currently below
      avg_deviation: average (price - MA) / MA across all tickers,
        weighted signal of HOW FAR below/above, not just count
      n_checked: how many tickers had enough data to evaluate
    """
    above_count = 0
    below_count = 0
    deviations = []

    for ticker in universe:
        if ticker not in px.columns:
            continue
        s = px.loc[:date, ticker].dropna()
        if len(s) < ma_window:
            continue

        ma = s.iloc[-ma_window:].mean()
        current = s.iloc[-1]
        if ma <= 0:
            continue

        deviation = (current - ma) / ma
        deviations.append(deviation)

        if current > ma:
            above_count += 1
        else:
            below_count += 1

    n_checked = above_count + below_count
    if n_checked == 0:
        return None

    return {
        "pct_above": above_count / n_checked,
        "pct_below": below_count / n_checked,
        "avg_deviation": float(np.mean(deviations)),
        "n_checked": n_checked,
    }


def validate_breadth_separation(px, universe, verbose=True):
    """
    Real stressed-vs-calm validation, same method used for every
    dial this session -- does breadth actually separate known
    crisis periods from known calm periods.
    """
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
    stressed_below_pcts = []
    for date_str, label in STRESSED_DATES:
        d = pd.Timestamp(date_str)
        result = compute_breadth(px, d, universe)
        if result:
            print(f"  {date_str} ({label}): "
                  f"pct_below={result['pct_below']:.1%} "
                  f"avg_dev={result['avg_deviation']:+.1%} "
                  f"n={result['n_checked']}")
            stressed_below_pcts.append(result['pct_below'])

    print()
    print("=== CALM DATES ===")
    calm_below_pcts = []
    for date_str, label in CALM_DATES:
        d = pd.Timestamp(date_str)
        result = compute_breadth(px, d, universe)
        if result:
            print(f"  {date_str} ({label}): "
                  f"pct_below={result['pct_below']:.1%} "
                  f"avg_dev={result['avg_deviation']:+.1%} "
                  f"n={result['n_checked']}")
            calm_below_pcts.append(result['pct_below'])

    print()
    if stressed_below_pcts and calm_below_pcts:
        s_mean = np.mean(stressed_below_pcts)
        c_mean = np.mean(calm_below_pcts)
        print(f"Stressed avg pct_below: {s_mean:.1%}")
        print(f"Calm avg pct_below:     {c_mean:.1%}")
        print(f"Separation: {s_mean - c_mean:+.1%}")


if __name__ == "__main__":
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    validate_breadth_separation(px, universe)
