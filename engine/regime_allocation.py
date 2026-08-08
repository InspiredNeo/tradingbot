"""
Allocation logic driven by the new 4-regime detector, replacing
the single scalar dial's continuous_allocation() function.

Starting with the two cleanest, most confidently-validated
regimes (CALM, SYSTEMIC_CRISIS) before building the nuanced
middle cases (CORRELATED_CALM, SCATTERED_WEAKNESS).
"""
from regime_detector import detect_regime


def get_regime_allocation(px, date, universe, current_equity=None):
    """
    Returns equity_target and a regime label, using the new
    breadth+correlation detector instead of the old scalar dial.

    CALM: aggressive, near-100% equity -- directly targets the
    confirmed calm-year drag problem (the actual reason this
    whole redesign started).

    SYSTEMIC_CRISIS: matches the existing, already-validated
    crisis posture (~30-40% equity, real defensive allocation) --
    not reinventing what already works.

    CORRELATED_CALM / SCATTERED_WEAKNESS: placeholder moderate
    posture for now -- will be refined once validated separately.
    """
    result = detect_regime(px, date, universe)
    if result is None:
        return {"equity_target": 0.70, "regime": "UNKNOWN"}  # safe fallback

    regime = result["regime"]

    if regime == "CALM":
        equity_target = 0.98
    elif regime == "SYSTEMIC_CRISIS":
        equity_target = 0.35
    elif regime == "CORRELATED_CALM":
        equity_target = 0.75  # placeholder, moderate
    elif regime == "SCATTERED_WEAKNESS":
        equity_target = 0.65  # placeholder, moderate-defensive
    else:
        equity_target = 0.70

    # Rate limiter -- same proven asymmetric pattern already
    # validated throughout this session (fast to de-risk, slow to
    # re-risk). Without this, a regime flip (e.g. CALM ->
    # SYSTEMIC_CRISIS in one week, entirely possible given both
    # breadth and correlation can shift meaningfully in a single
    # volatile week) would jump equity exposure instantly --
    # dangerous, not just suboptimal. This is a safety requirement,
    # not an optimization.
    DERISK_MAX = 0.15
    RERISK_MAX = 0.06

    raw_target = equity_target
    if current_equity is None:
        smoothed_equity = raw_target  # first call, no history to smooth from
    elif raw_target < current_equity:
        smoothed_equity = current_equity + max(raw_target - current_equity, -DERISK_MAX)
    else:
        smoothed_equity = current_equity + min(raw_target - current_equity, RERISK_MAX)

    return {
        "equity_target": smoothed_equity,
        "raw_target": raw_target,
        "regime": regime,
        "pct_below": result["pct_below"],
        "avg_correlation": result["avg_correlation"],
    }


if __name__ == "__main__":
    import pandas as pd
    import json
    import os

    DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    TEST_DATES = ["2008-11-15", "2013-06-15", "2017-06-15", "2022-06-15"]
    for date_str in TEST_DATES:
        d = pd.Timestamp(date_str)
        alloc = get_regime_allocation(px, d, universe)
        print(f"{date_str}: regime={alloc['regime']:<20} "
              f"equity_target={alloc['equity_target']:.2f}")
