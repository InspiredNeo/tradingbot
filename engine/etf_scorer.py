"""
ETF universe scoring -- Phase 1: scoring logic only.

Given a list of ETF tickers and a date, compute a composite score
per ETF based on:
  - momentum: 6-month return / volatility (risk-adjusted trend)
  - diversification: correlation to a reference basket (lower = better)
  - liquidity: proxy via price data availability/consistency
  - quality: simple proxy via drawdown behavior (smoother = better)

This does NOT decide what to hold or trade. It only ranks
candidates so we can sanity-check the ranking against dates we
already understand well before building anything that acts on it.
"""
import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

CANDIDATE_UNIVERSE = [
    "VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF",  # current universe
    "AGG", "TLT", "GLD",                          # current defensive
    "SOXX", "XLE", "XLK", "VNQ", "TIP",           # candidate additions
]


def _safe_series(px, ticker, date, min_days=126):
    if ticker not in px.columns:
        return None
    s = px.loc[:date, ticker].dropna()
    return s if len(s) >= min_days else None


def score_etf(px, ticker, date, reference_returns, lookback=252):
    """
    Score one ETF at one date. Returns dict of component scores
    (each roughly 0-1, higher = more attractive) plus composite.
    Returns None if there isn't enough history to score.
    """
    s = _safe_series(px, ticker, date)
    if s is None:
        return None

    rets = s.pct_change().dropna()
    if len(rets) < 126:
        return None

    # Momentum: 6-month (126 day) return divided by volatility
    mom_window = rets.iloc[-126:]
    mom_return = float((1 + mom_window).prod() - 1)
    mom_vol = float(mom_window.std() * np.sqrt(252))
    momentum_raw = mom_return / mom_vol if mom_vol > 0 else 0
    # Normalize into 0-1 via a soft cap -- raw values typically -2 to +3
    momentum_score = float(np.clip((momentum_raw + 1) / 4, 0, 1))

    # Diversification: correlation to reference basket (VTI+QQQ blend)
    # Lower correlation = more diversification value = higher score
    common_idx = rets.index.intersection(reference_returns.index)
    if len(common_idx) >= 60:
        corr = float(rets.loc[common_idx].corr(reference_returns.loc[common_idx]))
        diversification_score = float(np.clip(1 - abs(corr), 0, 1))
    else:
        diversification_score = 0.5  # unknown, neutral

    # Liquidity proxy: how much real trading history exists
    # (a genuine liquidity check would use volume; we don't have
    # volume data cached, so this is a placeholder using history
    # length as a rough stand-in -- flagged as a known limitation)
    liquidity_score = float(np.clip(len(s) / (lookback * 2), 0, 1))

    # Smoothness (renamed from "quality" -- this measures stability
    # of returns, NOT fund quality. True fund quality would need
    # expense ratio, AUM, tracking error -- none of which are
    # cached yet. Flagged as a real gap, not faked with a proxy.)
    # Lower vol-of-vol = smoother = higher score. This structurally
    # favors bonds/defensive assets, which is intentional given the
    # equilibrium-seeking goal, not a bug to hide.
    rolling_vol = rets.rolling(21).std().dropna()
    if len(rolling_vol) >= 20:
        vol_of_vol = float(rolling_vol.std())
        smoothness_score = float(np.clip(1 - vol_of_vol * 50, 0, 1))
    else:
        smoothness_score = 0.5

    # Composite: momentum is now a GATE, not just a weighted input.
    # Original formula let low correlation alone push flat/negative
    # momentum assets (bonds, gold) above strong performers during
    # genuine bull markets -- confirmed on real 2012/2017 data,
    # where AGG/GLD outranked VTI/QQQ despite VTI/QQQ having 3-8x
    # the six-month return. Diversification should refine WHICH
    # good assets to prefer, not override whether an asset is
    # actually attractive right now.
    #
    # Assets with raw_6mo_return below zero get a hard penalty
    # regardless of how diversified or "smooth" they look --
    # being uncorrelated to a falling market you're not even
    # invested in isn't a reason to rank something highly.
    momentum_gate = 1.0 if mom_return > 0 else 0.3

    composite = momentum_gate * (
        momentum_score * 0.55 +
        diversification_score * 0.15 +
        liquidity_score * 0.10 +
        smoothness_score * 0.20
    )

    return {
        "ticker": ticker,
        "momentum": round(momentum_score, 3),
        "diversification": round(diversification_score, 3),
        "liquidity": round(liquidity_score, 3),
        "smoothness": round(smoothness_score, 3),
        "fund_quality": None,  # not computable -- needs expense ratio/AUM/tracking error data
        "composite": round(composite, 3),
        "raw_6mo_return": round(mom_return, 4),
    }


def score_universe(date_str, universe=None, verbose=True):
    """
    Score every ETF in the universe at a given date.
    Returns a DataFrame sorted by composite score, highest first.
    """
    if universe is None:
        universe = CANDIDATE_UNIVERSE

    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)
    date = pd.Timestamp(date_str)

    # Build reference basket (VTI+QQQ blend) for diversification scoring
    ref_tickers = [t for t in ["VTI", "QQQ"] if t in px.columns]
    ref_series = px.loc[:date, ref_tickers].dropna(how="all")
    reference_returns = ref_series.pct_change().mean(axis=1).dropna()

    results = []
    for ticker in universe:
        score = score_etf(px, ticker, date, reference_returns)
        if score is not None:
            results.append(score)

    df = pd.DataFrame(results)
    if len(df) == 0:
        if verbose:
            print(f"No scoreable ETFs at {date_str}")
        return df

    df = df.sort_values("composite", ascending=False).reset_index(drop=True)

    if verbose:
        print(f"\nETF scores as of {date_str}:")
        print(df.to_string(index=False))

    return df


# Tier boundaries are PERCENTILES of that week's own score
# distribution, not fixed absolute numbers. This guarantees Tier 2
# is always populated (by construction, someone is in the middle
# 30%) -- its members are just genuinely weak in a bad year like
# 2022 and genuinely strong in a good year like 2017. Confirmed on
# real data: fixed thresholds left Tier 2 completely empty in 2022
# because the whole distribution shifted down, not because nothing
# was "second best" that week -- something always is, relatively.
TIER1_PERCENTILE = 0.75   # top 25% of this week's scores
TIER2_PERCENTILE = 0.40   # next 35% (between 40th and 75th pctile)
ABSOLUTE_TIER1_FLOOR = 0.35   # even if top 25% that week, must clear
                                # this to be called "Tier 1, full weight" --
                                # prevents the least-bad option in a broadly
                                # weak market from being mislabeled as strong
# below 40th percentile: excluded from holding, tracked only

MIN_CANDIDATES_FOR_PERCENTILE = 4  # need enough scores for percentile
                                     # cutoffs to mean anything


def select_universe(date_str, universe=None, verbose=True):
    """
    Percentile-based tiered selection -- relative to THIS WEEK's
    own score distribution, not a fixed absolute cutoff.

    Tier 1: top 25% of this week's scores -- full weight
    Tier 2: next 35% (40th-75th percentile) -- reduced weight, watched
    Tier 3: bottom 40% -- excluded from holding, tracked only

    Always populated (assuming enough candidates), so a bad market
    doesn't silently collapse Tier 2 to empty -- it shows what was
    relatively-better-than-worst even when everything was bad.

    Returns dict with 'tier1', 'tier2', 'tier3' ticker lists,
    each with their composite scores attached.
    """
    scores = score_universe(date_str, universe=universe, verbose=False)
    if len(scores) == 0:
        return {"tier1": [], "tier2": [], "tier3": []}

    if len(scores) < MIN_CANDIDATES_FOR_PERCENTILE:
        # Too few candidates for percentiles to be meaningful --
        # fall back to putting everyone in tier1 rather than
        # computing nonsense boundaries on 1-3 data points
        if verbose:
            print(f"\nOnly {len(scores)} candidates at {date_str} -- "
                  f"too few for percentile tiers, showing all as Tier 1")
        return {
            "tier1": list(zip(scores["ticker"], scores["composite"])),
            "tier2": [], "tier3": [],
        }

    composites = scores["composite"].values
    tier1_cutoff = float(np.percentile(composites, TIER1_PERCENTILE * 100))
    tier2_cutoff = float(np.percentile(composites, TIER2_PERCENTILE * 100))

    # Combine percentile ranking with an absolute floor. Percentile
    # alone falsely labeled GLD/AGG/TIP as "Tier 1, full weight" in
    # 2022 despite scores of 0.12-0.16 -- genuinely weak in absolute
    # terms, just relatively less bad that week. An absolute floor
    # (ABSOLUTE_TIER1_FLOOR) prevents anything below it from ever
    # being called Tier 1, no matter how it ranks against its peers.
    tier1 = scores[(scores["composite"] >= tier1_cutoff) &
                   (scores["composite"] >= ABSOLUTE_TIER1_FLOOR)]
    tier2 = scores[(scores["composite"] >= tier2_cutoff) &
                   (scores["composite"] < tier1_cutoff) |
                   ((scores["composite"] >= tier2_cutoff) &
                    (scores["composite"] < ABSOLUTE_TIER1_FLOOR) &
                    (scores["composite"] >= tier1_cutoff))]
    tier3 = scores[~scores["ticker"].isin(tier1["ticker"]) &
                   ~scores["ticker"].isin(tier2["ticker"])]

    if verbose:
        print(f"\nPercentile-tiered selection as of {date_str}:")
        print(f"  (Tier 1 cutoff this week: {tier1_cutoff:.3f}, "
              f"Tier 2 cutoff: {tier2_cutoff:.3f})")
        print(f"  TIER 1 (top 25%, full weight):")
        for _, row in tier1.iterrows():
            print(f"    {row['ticker']:<6} composite={row['composite']:.3f}  "
                  f"6mo_ret={row['raw_6mo_return']:+.1%}")
        print(f"  TIER 2 (next 35%, reduced weight, watched):")
        for _, row in tier2.iterrows():
            print(f"    {row['ticker']:<6} composite={row['composite']:.3f}  "
                  f"6mo_ret={row['raw_6mo_return']:+.1%}")
        print(f"  TIER 3 (bottom 40%, excluded, tracked only): "
              f"{len(tier3)} tickers")

    return {
        "tier1": list(zip(tier1["ticker"], tier1["composite"])),
        "tier2": list(zip(tier2["ticker"], tier2["composite"])),
        "tier3": list(zip(tier3["ticker"], tier3["composite"])),
    }


TIER2_SIZE_MULTIPLIER = 0.40  # Tier 2 positions get 40% the weight
                                 # a Tier 1 position of the same
                                 # relative score would get


def size_positions(date_str, universe=None, verbose=True):
    """
    Convert tiered selection into actual position weights.
    Pure function of the current week's scores -- no memory,
    no state, same discipline as the rate limiter.

    Within each tier, weight is proportional to score (not equal-
    weighted), so a 0.65 gets more than a 0.55 even in the same
    tier. Tier 2 positions are scaled down by TIER2_SIZE_MULTIPLIER
    relative to what the same score would earn in Tier 1.

    Returns dict of {ticker: weight}, weights sum to 1.0 across
    everything held (Tier 1 + Tier 2 combined). Tier 3 gets 0.
    """
    tiers = select_universe(date_str, universe=universe, verbose=False)

    raw_weights = {}
    for ticker, score in tiers["tier1"]:
        raw_weights[ticker] = score
    for ticker, score in tiers["tier2"]:
        raw_weights[ticker] = score * TIER2_SIZE_MULTIPLIER

    total = sum(raw_weights.values())
    if total == 0:
        if verbose:
            print(f"\nNo positions sizeable at {date_str}")
        return {}

    weights = {t: round(w / total, 4) for t, w in raw_weights.items()}

    if verbose:
        print(f"\nPosition weights as of {date_str}:")
        for t, w in sorted(weights.items(), key=lambda x: -x[1]):
            tier_label = "T1" if t in dict(tiers["tier1"]) else "T2"
            print(f"  {t:<6} {w:>6.1%}  [{tier_label}]")
        print(f"  (sum: {sum(weights.values()):.1%})")

    return weights


if __name__ == "__main__":
    # Quick sanity check across a few dates we already understand
    for d in ["2012-06-30", "2017-12-31", "2022-06-30"]:
        score_universe(d)
