"""
Combined regime detector: breadth + correlation, the two-part
signal replacing the single scalar dial approach. Validated
separately (breadth: 86.5pp separation, correlation: 24.5pp
separation but genuinely complements breadth's blind spot rather
than needing a fix -- confirmed via real data at 2013-06-15,
where high correlation coincided with still-positive average
returns, correctly read as "correlated calm/mild rotation" not
"correlated crisis").

Four real, distinct regimes based on the combination, not a
single blended number:
  LOW breadth stress + LOW correlation  = genuine calm
  LOW breadth stress + HIGH correlation = correlated calm/mild
                                           rotation (e.g. June 2013)
  HIGH breadth stress + LOW correlation = scattered/idiosyncratic
                                           weakness, not systemic
  HIGH breadth stress + HIGH correlation = genuine systemic crisis
                                           (highest confidence signal)
"""
import os
import pandas as pd
import json

from market_breadth import compute_breadth
from market_correlation import compute_correlation

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

# Thresholds derived from the real validation data:
# breadth stressed avg 96.6%, calm avg 10.2% -- midpoint-ish,
# biased toward the calm side since calm dates clustered tightly
# (4.7-22.8%) while stressed dates clustered even more tightly
# (94.6-98.1%) -- a wide gap to place a threshold in safely
BREADTH_STRESS_THRESHOLD = 0.40

# correlation stressed avg 0.833, calm avg 0.588 -- real but
# weaker separation, threshold placed conservatively
CORR_HIGH_THRESHOLD = 0.70


def detect_regime(px, date, universe):
    breadth = compute_breadth(px, date, universe)
    corr = compute_correlation(px, date)

    if breadth is None or corr is None:
        return None

    breadth_stressed = breadth["pct_below"] >= BREADTH_STRESS_THRESHOLD
    corr_high = corr["avg_correlation"] >= CORR_HIGH_THRESHOLD

    if not breadth_stressed and not corr_high:
        regime = "CALM"
    elif not breadth_stressed and corr_high:
        regime = "CORRELATED_CALM"
    elif breadth_stressed and not corr_high:
        regime = "SCATTERED_WEAKNESS"
    else:
        regime = "SYSTEMIC_CRISIS"

    return {
        "regime": regime,
        "pct_below": breadth["pct_below"],
        "avg_deviation": breadth["avg_deviation"],
        "avg_correlation": corr["avg_correlation"],
    }


if __name__ == "__main__":
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    TEST_DATES = [
        ("2008-11-15", "2008 crisis depth -- expect SYSTEMIC_CRISIS"),
        ("2009-02-27", "2008-09 crisis trough -- expect SYSTEMIC_CRISIS"),
        ("2020-03-20", "COVID crash -- expect SYSTEMIC_CRISIS"),
        ("2022-06-15", "2022 rate crisis -- expect SYSTEMIC_CRISIS"),
        ("2013-06-15", "Taper Tantrum peak -- expect CORRELATED_CALM (real, validated case)"),
        ("2005-06-15", "calm mid-2000s -- expect CALM"),
        ("2017-06-15", "calm mid-2017 -- expect CALM"),
        ("2021-06-15", "calm mid-2021 -- expect CALM"),
    ]

    print(f"{'Date':<12} {'Regime':<20} {'pct_below':<10} {'avg_corr':<10} {'Note'}")
    for date_str, note in TEST_DATES:
        d = pd.Timestamp(date_str)
        result = detect_regime(px, d, universe)
        if result:
            print(f"{date_str:<12} {result['regime']:<20} "
                  f"{result['pct_below']:<10.1%} {result['avg_correlation']:<10.3f} {note}")
        else:
            print(f"{date_str:<12} FAILED TO COMPUTE")
