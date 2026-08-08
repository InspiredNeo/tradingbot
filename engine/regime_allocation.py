"""
Allocation logic driven by the new 4-regime detector, replacing
the single scalar dial's continuous_allocation() function.

Starting with the two cleanest, most confidently-validated
regimes (CALM, SYSTEMIC_CRISIS) before building the nuanced
middle cases (CORRELATED_CALM, SCATTERED_WEAKNESS).
"""
from regime_detector import detect_regime


def get_regime_allocation(px, date, universe, current_equity=None,
                          breadth_history=None, previously_severe=None,
                          corr_history=None, previously_corr_high=None,
                          regime_history=None):
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
    from market_correlation import compute_correlation
    corr_result = compute_correlation(px, date)

    result = detect_regime(px, date, universe,
                           breadth_history=breadth_history,
                           previously_severe=previously_severe,
                           corr_history=corr_history,
                           previously_corr_high=previously_corr_high,
                           regime_history=regime_history)
    if result is None:
        return {"equity_target": 0.70, "regime": "UNKNOWN"}  # safe fallback

    regime = result["regime"]

    # MERGED after real evidence: a larger, 16-year sample (n=385
    # CALM, n=268 CORRELATED_CALM) showed nearly IDENTICAL real
    # forward returns (+0.89% vs +1.03% mean) -- once breadth
    # already confirms genuine calm, knowing whether that calm is
    # correlated doesn't change the right allocation. Correlation
    # remains a real, valid signal used elsewhere in classification
    # (e.g. correctly distinguishing the June 2013 case) -- just
    # doesn't need its own separate allocation tier.
    if regime in ("CALM", "CORRELATED_CALM"):
        equity_target = 0.98
    elif regime == "SYSTEMIC_CRISIS":
        equity_target = 0.35
    elif regime == "MODERATE_STRESS":
        equity_target = 0.55  # real, distinct tier -- between calm
                                # and crisis, for events like Feb 2008
                                # pre-crisis decline, 2011 debt ceiling,
                                # or a slow grinding bear like 2022
    elif regime == "SCATTERED_WEAKNESS":
        # FIXED based on real 16-year evidence: this was the ONLY
        # regime with a clearly NEGATIVE mean forward return
        # (-3.95%), and by far the highest volatility (0.112,
        # roughly double every other regime's). The 0.65 placeholder
        # was set by feel -- real data supports MORE caution here.
        equity_target = 0.45
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
        # State to thread forward to the NEXT call, same pure-
        # function pattern as current_equity -- caller must save
        # these and pass them back in as breadth_history (append
        # pct_below), corr_history (append avg_correlation),
        # previously_severe, previously_corr_high, and
        # regime_history (append regime) on the following week
        "severely_stressed": result.get("severely_stressed"),
        "corr_high": result.get("corr_high"),
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
