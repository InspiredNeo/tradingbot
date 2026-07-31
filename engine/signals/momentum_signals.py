"""
Momentum Signals for Market Terminal Bot Engine.
8 momentum signals across different dimensions.

Signals:
1.  Cross-asset momentum (stocks vs bonds vs commodities)
2.  Sector momentum (which sectors leading/lagging)
3.  Factor momentum (value vs growth vs quality vs low-vol)
4.  International vs domestic momentum
5.  Time-series momentum 1M
6.  Time-series momentum 3M
7.  Time-series momentum 6M
8.  Time-series momentum 12M
"""

import os
import time
import numpy as np
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cache
_cache = {}
_cache_ts = {}
CACHE_TTL = 3600  # 1 hour


def _cached(key, fn, ttl=CACHE_TTL):
    now = time.time()
    if key in _cache and now - _cache_ts.get(key, 0) < ttl:
        return _cache[key]
    result = fn()
    _cache[key] = result
    _cache_ts[key] = now
    return result


def _fetch_price(ticker, period="1y"):
    try:
        hist = yf.Ticker(ticker).history(period=period)
        return hist["Close"].dropna()
    except Exception:
        return pd.Series(dtype=float)


def _momentum(series, lookback=20):
    """Return (lookback)-day momentum as a fraction."""
    if len(series) < lookback + 1:
        return 0.0
    return float((series.iloc[-1] - series.iloc[-lookback-1]) /
                 series.iloc[-lookback-1])


def _rank_momentum(tickers_dict, lookback=60):
    """
    Fetch prices for a dict of {name: ticker} and rank by momentum.
    Returns sorted list of (name, momentum) tuples.
    """
    prices = {}
    def fetch_one(item):
        name, ticker = item
        p = _fetch_price(ticker, period="1y")
        if not p.empty:
            return name, _momentum(p, lookback)
        return name, 0.0

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_one, item): item
                   for item in tickers_dict.items()}
        for future in as_completed(futures):
            name, mom = future.result()
            prices[name] = mom

    return sorted(prices.items(), key=lambda x: x[1], reverse=True)


# ── Signal functions ───────────────────────────────────────────

def get_cross_asset_momentum():
    """
    Compare momentum across major asset classes.
    Tells us which asset class is leading — critical for allocation.
    """
    def _fetch():
        assets = {
            "US_Stocks": "SPY",
            "Intl_Stocks": "VXUS",
            "Bonds": "BND",
            "Gold": "GC=F",
            "Commodities": "DJP",
            "Real_Estate": "VNQ",
        }
        ranked = _rank_momentum(assets, lookback=60)

        # Top asset class gets overweight signal
        top = ranked[0][0] if ranked else "US_Stocks"
        bottom = ranked[-1][0] if ranked else "Bonds"

        # Stock/bond relative momentum
        stocks_mom = next((m for n, m in ranked if n == "US_Stocks"), 0)
        bonds_mom = next((m for n, m in ranked if n == "Bonds"), 0)
        risk_on = stocks_mom > bonds_mom

        return {
            "ranked": ranked,
            "top_asset": top,
            "bottom_asset": bottom,
            "risk_on": risk_on,
            "stock_bond_spread": stocks_mom - bonds_mom,
            "signal": "risk_on" if risk_on else "risk_off",
        }
    return _cached("cross_asset", _fetch)


def get_sector_momentum():
    """
    Rank all 11 S&P sectors by 3-month momentum.
    Tells us which sectors to overweight/underweight.
    """
    def _fetch():
        sectors = {
            "Technology": "XLK",
            "Healthcare": "XLV",
            "Financials": "XLF",
            "Energy": "XLE",
            "Industrials": "XLI",
            "Consumer_Disc": "XLY",
            "Consumer_Staples": "XLP",
            "Utilities": "XLU",
            "Materials": "XLB",
            "Real_Estate": "XLRE",
            "Communication": "XLC",
        }
        ranked = _rank_momentum(sectors, lookback=60)

        # Categorize leaders and laggards
        leaders = [n for n, m in ranked[:3]]
        laggards = [n for n, m in ranked[-3:]]

        # Defensive vs cyclical rotation signal
        defensive = {"Utilities", "Consumer_Staples", "Healthcare"}
        cyclical = {"Technology", "Financials", "Energy", "Industrials",
                    "Consumer_Disc"}

        top_3 = set(leaders)
        defensive_leading = len(top_3 & defensive) >= 2
        cyclical_leading = len(top_3 & cyclical) >= 2

        return {
            "ranked": ranked,
            "leaders": leaders,
            "laggards": laggards,
            "defensive_leading": defensive_leading,
            "cyclical_leading": cyclical_leading,
            "signal": "defensive_rotation" if defensive_leading
                      else "cyclical_rotation" if cyclical_leading
                      else "mixed",
        }
    return _cached("sector_mom", _fetch)


def get_factor_momentum():
    """
    Factor momentum: which investment factors are working.
    Value, Growth, Quality, Low Volatility, Momentum itself.
    """
    def _fetch():
        factors = {
            "Value": "VTV",
            "Growth": "VUG",
            "Quality": "QUAL",
            "Low_Vol": "USMV",
            "Momentum": "MTUM",
            "Small_Cap": "IWM",
            "Dividend": "VYM",
        }
        ranked = _rank_momentum(factors, lookback=60)
        top_factor = ranked[0][0] if ranked else "Growth"

        # Risk appetite signal from factor leadership
        risk_factors = {"Growth", "Momentum", "Small_Cap"}
        defensive_factors = {"Low_Vol", "Quality", "Dividend", "Value"}
        top_3 = {n for n, _ in ranked[:3]}

        risk_appetite = len(top_3 & risk_factors) >= 2

        return {
            "ranked": ranked,
            "top_factor": top_factor,
            "risk_appetite": risk_appetite,
            "signal": "risk_seeking" if risk_appetite else "defensive",
        }
    return _cached("factor_mom", _fetch)


def get_intl_vs_domestic():
    """
    International vs domestic momentum.
    Tells us whether to tilt toward US or international ETFs.
    """
    def _fetch():
        markets = {
            "US_Large": "SPY",
            "US_Small": "IWM",
            "Developed_Intl": "EFA",
            "Emerging": "EEM",
            "Europe": "VGK",
            "Asia_Pacific": "VPL",
            "EM_Asia": "AAXJ",
        }
        ranked = _rank_momentum(markets, lookback=60)

        us_mom = np.mean([m for n, m in ranked
                          if n in ("US_Large", "US_Small")])
        intl_mom = np.mean([m for n, m in ranked
                            if n in ("Developed_Intl", "Emerging",
                                     "Europe", "Asia_Pacific")])
        em_mom = next((m for n, m in ranked if n == "Emerging"), 0)
        dev_mom = next((m for n, m in ranked if n == "Developed_Intl"), 0)

        return {
            "ranked": ranked,
            "us_momentum": us_mom,
            "intl_momentum": intl_mom,
            "em_momentum": em_mom,
            "developed_momentum": dev_mom,
            "us_outperforming": us_mom > intl_mom,
            "em_outperforming": em_mom > dev_mom,
            "signal": "favor_us" if us_mom > intl_mom else "favor_intl",
        }
    return _cached("intl_vs_dom", _fetch)


def get_time_series_momentum():
    """
    Time-series momentum for the broad market (SPY) across
    1M, 3M, 6M, 12M lookback windows.
    Classic trend-following signal.
    """
    def _fetch():
        spy = _fetch_price("SPY", period="2y")
        if spy.empty:
            return {
                "mom_1m": 0.0, "mom_3m": 0.0,
                "mom_6m": 0.0, "mom_12m": 0.0,
                "composite": 0.0, "signal": "neutral",
            }

        mom_1m = _momentum(spy, 21)
        mom_3m = _momentum(spy, 63)
        mom_6m = _momentum(spy, 126)
        mom_12m = _momentum(spy, 252)

        # Composite: weight shorter lookbacks more
        composite = (mom_1m * 0.1 + mom_3m * 0.2 +
                     mom_6m * 0.3 + mom_12m * 0.4)

        # Count positive lookbacks
        positive = sum([mom_1m > 0, mom_3m > 0,
                        mom_6m > 0, mom_12m > 0])

        signal = "strong_uptrend" if positive == 4 else \
                 "uptrend" if positive == 3 else \
                 "downtrend" if positive <= 1 else "mixed"

        return {
            "mom_1m": mom_1m,
            "mom_3m": mom_3m,
            "mom_6m": mom_6m,
            "mom_12m": mom_12m,
            "composite": composite,
            "positive_lookbacks": positive,
            "signal": signal,
        }
    return _cached("ts_momentum", _fetch)


# ── Master collector ───────────────────────────────────────────

def get_all_momentum_signals(verbose=False):
    """
    Fetch all 8 momentum signals in parallel.
    Returns raw signals + 14-feature vector.
    """
    signal_fns = {
        "cross_asset": get_cross_asset_momentum,
        "sector": get_sector_momentum,
        "factor": get_factor_momentum,
        "intl_vs_dom": get_intl_vs_domestic,
        "ts_momentum": get_time_series_momentum,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): name
                   for name, fn in signal_fns.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e)}

    if verbose:
        _print_signals(results)

    vector = _to_feature_vector(results)
    return results, vector


def _to_feature_vector(signals):
    """Convert to normalized numpy array for regime detection."""
    ca = signals.get("cross_asset", {})
    sec = signals.get("sector", {})
    fac = signals.get("factor", {})
    intl = signals.get("intl_vs_dom", {})
    ts = signals.get("ts_momentum", {})

    vector = np.array([
        # Cross-asset (2)
        np.clip(ca.get("stock_bond_spread", 0) * 10, -3, 3),
        1.0 if ca.get("risk_on") else -1.0,

        # Sector (2)
        1.0 if sec.get("cyclical_leading") else 0.0,
        -1.0 if sec.get("defensive_leading") else 0.0,

        # Factor (2)
        1.0 if fac.get("risk_appetite") else -1.0,
        np.clip(next((m for n, m in fac.get("ranked", [])
                      if n == "Momentum"), 0) * 10, -3, 3),

        # International (3)
        np.clip((intl.get("us_momentum", 0) -
                 intl.get("intl_momentum", 0)) * 10, -3, 3),
        np.clip(intl.get("em_momentum", 0) * 10, -3, 3),
        np.clip(intl.get("developed_momentum", 0) * 10, -3, 3),

        # Time-series momentum (5)
        np.clip(ts.get("mom_1m", 0) * 10, -3, 3),
        np.clip(ts.get("mom_3m", 0) * 10, -3, 3),
        np.clip(ts.get("mom_6m", 0) * 10, -3, 3),
        np.clip(ts.get("mom_12m", 0) * 10, -3, 3),
        np.clip(ts.get("composite", 0) * 10, -3, 3),
    ], dtype=np.float32)

    return vector  # 14 features


def _print_signals(signals):
    print("\n" + "=" * 50)
    print("MOMENTUM SIGNALS")
    print("=" * 50)

    ca = signals.get("cross_asset", {})
    print(f"\nCross-Asset: {ca.get('signal', 'N/A').upper()}")
    print(f"  Top: {ca.get('top_asset')} | "
          f"Bottom: {ca.get('bottom_asset')}")
    print(f"  Stock/Bond spread: "
          f"{ca.get('stock_bond_spread', 0)*100:.1f}%")

    sec = signals.get("sector", {})
    print(f"\nSector: {sec.get('signal', 'N/A').upper()}")
    print(f"  Leaders: {', '.join(sec.get('leaders', []))}")
    print(f"  Laggards: {', '.join(sec.get('laggards', []))}")

    fac = signals.get("factor", {})
    print(f"\nFactor: {fac.get('signal', 'N/A').upper()}")
    print(f"  Top factor: {fac.get('top_factor')}")
    ranked = fac.get("ranked", [])
    if ranked:
        print(f"  Ranking: " +
              " > ".join(f"{n}({m*100:.1f}%)"
                         for n, m in ranked[:4]))

    intl = signals.get("intl_vs_dom", {})
    print(f"\nIntl vs Domestic: {intl.get('signal', 'N/A').upper()}")
    print(f"  US: {intl.get('us_momentum', 0)*100:.1f}% | "
          f"Intl: {intl.get('intl_momentum', 0)*100:.1f}% | "
          f"EM: {intl.get('em_momentum', 0)*100:.1f}%")

    ts = signals.get("ts_momentum", {})
    print(f"\nTime-Series: {ts.get('signal', 'N/A').upper()}")
    print(f"  1M: {ts.get('mom_1m', 0)*100:.1f}% | "
          f"3M: {ts.get('mom_3m', 0)*100:.1f}% | "
          f"6M: {ts.get('mom_6m', 0)*100:.1f}% | "
          f"12M: {ts.get('mom_12m', 0)*100:.1f}%")
    print(f"  Composite: {ts.get('composite', 0)*100:.1f}% "
          f"({ts.get('positive_lookbacks')}/4 positive)")
    print("=" * 50)


if __name__ == "__main__":
    import time
    print("Fetching momentum signals...")
    t = time.time()
    signals, vector = get_all_momentum_signals(verbose=True)
    print(f"\nFetch time: {time.time()-t:.2f}s")
    print(f"Feature vector: {vector.shape} → {vector}")
