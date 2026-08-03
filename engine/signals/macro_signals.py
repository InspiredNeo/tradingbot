"""
Macro Signals for Market Terminal Bot Engine.
8 macroeconomic signals from FRED.

Signals:
1.  ISM Manufacturing PMI
2.  ISM Services PMI
3.  Unemployment rate trend
4.  CPI momentum (inflation accelerating/decelerating)
5.  Fed funds rate vs neutral rate
6.  GDP growth momentum
7.  Consumer confidence
8.  Leading economic indicators composite
"""

import os
import time
import numpy as np
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
FRED_KEY = os.getenv("FRED_API_KEY")

# Cache - macro data changes monthly so cache aggressively
_cache = {}
_cache_ts = {}
CACHE_TTL = 86400  # 24 hours


def _cached(key, fn, ttl=CACHE_TTL):
    now = time.time()
    if key in _cache and now - _cache_ts.get(key, 0) < ttl:
        return _cache[key]
    result = fn()
    _cache[key] = result
    _cache_ts[key] = now
    return result


def _fetch_fred(series_id, limit=24):
    """Fetch FRED series, return pandas Series."""
    try:
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": FRED_KEY,
                    "file_type": "json", "sort_order": "desc",
                    "limit": limit},
            timeout=15,
        )
        obs = resp.json().get("observations", [])
        dates, values = [], []
        for o in reversed(obs):
            v = o.get("value", ".")
            if v != ".":
                dates.append(pd.to_datetime(o["date"]))
                values.append(float(v))
        return pd.Series(values, index=dates)
    except Exception:
        return pd.Series(dtype=float)


def _momentum(series, periods=3):
    """N-period momentum."""
    if len(series) < periods + 1:
        return 0.0
    return float(series.iloc[-1] - series.iloc[-periods - 1])


def _zscore(series, window=12):
    """Z-score vs rolling window."""
    if len(series) < 4:
        return 0.0
    recent = series.iloc[-min(window, len(series)):]
    mu, sigma = recent.mean(), recent.std()
    return float((series.iloc[-1] - mu) / sigma) if sigma > 0 else 0.0


# ── Signal functions ───────────────────────────────────────────

def get_ism_manufacturing():
    """
    ISM Manufacturing PMI.
    Above 50 = expansion. Below 50 = contraction.
    Leading indicator for industrial activity and earnings.
    """
    def _fetch():
        pmi = _fetch_fred("MANEMP", 24)  # Manufacturing employment proxy
        # Use ISM via FRED
        ism = _fetch_fred("ISM/MAN_PMI", 24)
        if ism.empty:
            # Fallback: use industrial production
            ip = _fetch_fred("INDPRO", 24)
            if ip.empty:
                return {"level": 50.0, "momentum": 0.0,
                        "expanding": True, "signal": "neutral"}
            level = float(ip.iloc[-1])
            mom = _momentum(ip, 3)
            return {"level": level, "momentum": mom,
                    "expanding": mom > 0, "signal": "expanding" if mom > 0 else "contracting"}

        level = float(ism.iloc[-1])
        mom = _momentum(ism, 3)
        expanding = level > 50
        accelerating = mom > 0

        return {
            "level": level,
            "momentum": mom,
            "expanding": expanding,
            "accelerating": accelerating,
            "signal": "strong" if expanding and accelerating else
                      "expanding" if expanding else
                      "contracting" if not expanding and not accelerating else
                      "recovering",
        }
    return _cached("ism_mfg", _fetch)


def get_ism_services():
    """
    ISM Services PMI.
    Services = ~70% of US economy. More important than manufacturing.
    """
    def _fetch():
        ism = _fetch_fred("ISM/NONMAN_NMI", 24)
        if ism.empty:
            # Fallback: retail sales
            retail = _fetch_fred("RSAFS", 24)
            if retail.empty:
                return {"level": 50.0, "momentum": 0.0, "signal": "neutral"}
            level = float(retail.iloc[-1])
            mom = _momentum(retail, 3)
            return {"level": level, "momentum": mom,
                    "expanding": mom > 0,
                    "signal": "expanding" if mom > 0 else "contracting"}

        level = float(ism.iloc[-1])
        mom = _momentum(ism, 3)
        return {
            "level": level,
            "momentum": mom,
            "expanding": level > 50,
            "signal": "strong" if level > 55 else
                      "expanding" if level > 50 else "contracting",
        }
    return _cached("ism_svc", _fetch)


def get_unemployment_trend():
    """
    Unemployment rate trend.
    Rising unemployment = economic weakness = risk-off.
    The Sahm Rule: if 3M avg unemployment rises 0.5% above 12M low = recession.
    """
    def _fetch():
        unrate = _fetch_fred("UNRATE", 24)
        if unrate.empty:
            return {"level": 4.0, "trend": 0.0,
                    "sahm_rule": False, "signal": "neutral"}

        level = float(unrate.iloc[-1])
        trend_3m = _momentum(unrate, 3)
        trend_6m = _momentum(unrate, 6)

        # Sahm Rule calculation
        avg_3m = unrate.iloc[-3:].mean() if len(unrate) >= 3 else level
        min_12m = unrate.iloc[-12:].min() if len(unrate) >= 12 else level
        sahm_indicator = avg_3m - min_12m
        sahm_triggered = sahm_indicator >= 0.5

        signal = "recession_warning" if sahm_triggered else \
                 "deteriorating" if trend_3m > 0.2 else \
                 "improving" if trend_3m < -0.1 else "stable"

        return {
            "level": level,
            "trend_3m": trend_3m,
            "trend_6m": trend_6m,
            "sahm_indicator": float(sahm_indicator),
            "sahm_triggered": sahm_triggered,
            "signal": signal,
        }
    return _cached("unemployment", _fetch)


def get_cpi_momentum():
    """
    CPI inflation momentum.
    Accelerating inflation = Fed tightening risk = bearish for bonds.
    Decelerating = Fed easing potential = bullish.
    """
    def _fetch():
        cpi = _fetch_fred("CPIAUCSL", 24)
        if cpi.empty:
            return {"yoy": 3.0, "momentum": 0.0, "signal": "neutral"}

        # Year-over-year inflation
        if len(cpi) >= 13:
            yoy = float((cpi.iloc[-1] / cpi.iloc[-13] - 1) * 100)
        else:
            yoy = 3.0

        # 3-month momentum (is inflation accelerating or decelerating?)
        if len(cpi) >= 4:
            mom_3m = float((cpi.iloc[-1] / cpi.iloc[-4] - 1) * 100 * 4)  # annualized
        else:
            mom_3m = yoy

        acceleration = mom_3m - yoy  # positive = accelerating

        signal = "high_inflation" if yoy > 4 else \
                 "accelerating" if acceleration > 0.5 else \
                 "decelerating" if acceleration < -0.5 else \
                 "stable"

        return {
            "yoy": yoy,
            "momentum_3m_annualized": mom_3m,
            "acceleration": acceleration,
            "signal": signal,
        }
    return _cached("cpi", _fetch)


def get_fed_policy():
    """
    Fed funds rate vs estimated neutral rate.
    Restrictive policy (above neutral) = headwind for growth.
    Accommodative (below neutral) = tailwind.
    """
    def _fetch():
        fedfunds = _fetch_fred("FEDFUNDS", 24)
        if fedfunds.empty:
            return {"rate": 5.0, "stance": "neutral", "signal": "neutral"}

        current_rate = float(fedfunds.iloc[-1])
        trend = _momentum(fedfunds, 6)

        # Estimated neutral rate (r*) — roughly 2.5% historically
        # In current environment, Fed estimates ~2.5-3%
        neutral_rate = 2.75
        spread_to_neutral = current_rate - neutral_rate

        stance = "very_restrictive" if spread_to_neutral > 2 else \
                 "restrictive" if spread_to_neutral > 0.5 else \
                 "neutral" if abs(spread_to_neutral) <= 0.5 else \
                 "accommodative"

        # Is Fed cutting or hiking?
        direction = "cutting" if trend < -0.1 else \
                    "hiking" if trend > 0.1 else "on_hold"

        signal = "bearish" if stance in ("very_restrictive", "restrictive") \
                              and direction == "hiking" else \
                 "bullish" if stance == "accommodative" or direction == "cutting" else \
                 "neutral"

        return {
            "rate": current_rate,
            "neutral_rate": neutral_rate,
            "spread_to_neutral": spread_to_neutral,
            "stance": stance,
            "direction": direction,
            "signal": signal,
        }
    return _cached("fed_policy", _fetch)


def get_gdp_momentum():
    """
    GDP growth momentum.
    Quarterly GDP growth trend.
    """
    def _fetch():
        gdp = _fetch_fred("A191RL1Q225SBEA", 12)  # Real GDP growth rate
        if gdp.empty:
            return {"latest": 2.5, "trend": 0.0, "signal": "neutral"}

        latest = float(gdp.iloc[-1])
        trend = _momentum(gdp, 2)  # 2-quarter trend
        avg_4q = float(gdp.iloc[-4:].mean()) if len(gdp) >= 4 else latest

        signal = "strong" if latest > 3 and trend > 0 else \
                 "expanding" if latest > 0 else \
                 "contracting" if latest < 0 else "slowing"

        return {
            "latest_quarter": latest,
            "trend_2q": trend,
            "avg_4q": avg_4q,
            "signal": signal,
        }
    return _cached("gdp", _fetch)


def get_consumer_confidence():
    """
    Consumer confidence index.
    High confidence = more spending = economic growth.
    Sharp drops = warning signal.
    """
    def _fetch():
        # University of Michigan Consumer Sentiment
        umcsent = _fetch_fred("UMCSENT", 24)
        if umcsent.empty:
            return {"level": 70.0, "zscore": 0.0, "signal": "neutral"}

        level = float(umcsent.iloc[-1])
        zscore = _zscore(umcsent)
        trend = _momentum(umcsent, 3)

        signal = "strong" if level > 90 else \
                 "positive" if level > 75 else \
                 "weak" if level < 60 else \
                 "negative" if level < 50 else "neutral"

        return {
            "level": level,
            "zscore": zscore,
            "trend_3m": trend,
            "signal": signal,
        }
    return _cached("consumer_conf", _fetch)


def get_leading_indicators():
    """
    Conference Board Leading Economic Index.
    Composite of 10 leading indicators.
    Consecutive monthly declines = recession warning.
    """
    def _fetch():
        lei = _fetch_fred("USSLIND", 24)
        if lei.empty:
            # Fallback: use yield curve + stock market composite
            return {"level": 100.0, "trend": 0.0,
                    "consecutive_declines": 0, "signal": "neutral"}

        level = float(lei.iloc[-1])
        trend_3m = _momentum(lei, 3)
        trend_6m = _momentum(lei, 6)

        # Count consecutive monthly declines
        consec_declines = 0
        for i in range(len(lei) - 1, 0, -1):
            if lei.iloc[i] < lei.iloc[i-1]:
                consec_declines += 1
            else:
                break

        # 6+ consecutive declines historically precede recessions
        signal = "recession_warning" if consec_declines >= 6 else \
                 "caution" if consec_declines >= 3 else \
                 "improving" if trend_3m > 0 else "neutral"

        return {
            "level": level,
            "trend_3m": trend_3m,
            "trend_6m": trend_6m,
            "consecutive_declines": consec_declines,
            "signal": signal,
        }
    return _cached("lei", _fetch)


# ── Master collector ───────────────────────────────────────────

def get_all_macro_signals(verbose=False):
    """Fetch all 8 macro signals in parallel."""
    signal_fns = {
        "ism_mfg": get_ism_manufacturing,
        "ism_svc": get_ism_services,
        "unemployment": get_unemployment_trend,
        "cpi": get_cpi_momentum,
        "fed": get_fed_policy,
        "gdp": get_gdp_momentum,
        "consumer": get_consumer_confidence,
        "lei": get_leading_indicators,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fn): name
                   for name, fn in signal_fns.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e), "signal": "neutral"}

    if verbose:
        _print_signals(results)

    vector = _to_feature_vector(results)
    return results, vector


def _to_feature_vector(signals):
    ism_m = signals.get("ism_mfg", {})
    ism_s = signals.get("ism_svc", {})
    unemp = signals.get("unemployment", {})
    cpi = signals.get("cpi", {})
    fed = signals.get("fed", {})
    gdp = signals.get("gdp", {})
    cons = signals.get("consumer", {})
    lei = signals.get("lei", {})

    vector = np.array([
        # ISM Manufacturing (2)
        np.clip((ism_m.get("level", 50) - 50) / 10, -3, 3),
        np.clip(ism_m.get("momentum", 0), -3, 3),

        # ISM Services (2)
        np.clip((ism_s.get("level", 50) - 50) / 10, -3, 3),
        np.clip(ism_s.get("momentum", 0), -3, 3),

        # Unemployment (2)
        np.clip(-unemp.get("trend_3m", 0) * 10, -3, 3),
        -1.0 if unemp.get("sahm_triggered") else 0.0,

        # CPI (2)
        np.clip(-(cpi.get("acceleration", 0)), -3, 3),
        np.clip((3.0 - cpi.get("yoy", 3.0)) / 2, -3, 3),

        # Fed policy (2)
        np.clip(-fed.get("spread_to_neutral", 0) / 2, -3, 3),
        1.0 if fed.get("direction") == "cutting" else
        -1.0 if fed.get("direction") == "hiking" else 0.0,

        # GDP (2)
        np.clip(gdp.get("latest_quarter", 2) / 3, -3, 3),
        np.clip(gdp.get("trend_2q", 0), -3, 3),

        # Consumer confidence (2)
        np.clip(cons.get("zscore", 0), -3, 3),
        np.clip(cons.get("trend_3m", 0) / 5, -3, 3),

        # LEI (2)
        np.clip(lei.get("trend_3m", 0) / 2, -3, 3),
        np.clip(-lei.get("consecutive_declines", 0) / 3, -3, 0),
    ], dtype=np.float32)

    return vector  # 16 features


def _print_signals(signals):
    print("\n" + "=" * 50)
    print("MACRO SIGNALS")
    print("=" * 50)

    ism_m = signals.get("ism_mfg", {})
    print(f"\nISM Manufacturing: {ism_m.get('signal', 'N/A').upper()}")
    print(f"  Level: {ism_m.get('level', 0):.1f} | "
          f"Momentum: {ism_m.get('momentum', 0):.2f}")

    ism_s = signals.get("ism_svc", {})
    print(f"\nISM Services: {ism_s.get('signal', 'N/A').upper()}")
    print(f"  Level: {ism_s.get('level', 0):.1f} | "
          f"Momentum: {ism_s.get('momentum', 0):.2f}")

    u = signals.get("unemployment", {})
    print(f"\nUnemployment: {u.get('signal', 'N/A').upper()}")
    print(f"  Rate: {u.get('level', 0):.1f}% | "
          f"3M trend: {u.get('trend_3m', 0):+.2f}% | "
          f"Sahm: {u.get('sahm_indicator', 0):.2f} "
          f"{'⚠️ TRIGGERED' if u.get('sahm_triggered') else ''}")

    c = signals.get("cpi", {})
    print(f"\nInflation (CPI): {c.get('signal', 'N/A').upper()}")
    print(f"  YoY: {c.get('yoy', 0):.1f}% | "
          f"3M annualized: {c.get('momentum_3m_annualized', 0):.1f}% | "
          f"Acceleration: {c.get('acceleration', 0):+.2f}%")

    f = signals.get("fed", {})
    print(f"\nFed Policy: {f.get('stance', 'N/A').upper()} "
          f"({f.get('direction', 'N/A').upper()})")
    print(f"  Rate: {f.get('rate', 0):.2f}% | "
          f"Neutral: {f.get('neutral_rate', 0):.2f}% | "
          f"Spread: {f.get('spread_to_neutral', 0):+.2f}%")

    g = signals.get("gdp", {})
    print(f"\nGDP: {g.get('signal', 'N/A').upper()}")
    print(f"  Latest Q: {g.get('latest_quarter', 0):.1f}% | "
          f"4Q avg: {g.get('avg_4q', 0):.1f}% | "
          f"Trend: {g.get('trend_2q', 0):+.2f}%")

    cc = signals.get("consumer", {})
    print(f"\nConsumer Confidence: {cc.get('signal', 'N/A').upper()}")
    print(f"  Level: {cc.get('level', 0):.1f} | "
          f"Z-score: {cc.get('zscore', 0):.2f} | "
          f"3M trend: {cc.get('trend_3m', 0):+.2f}")

    l = signals.get("lei", {})
    print(f"\nLeading Indicators: {l.get('signal', 'N/A').upper()}")
    print(f"  Level: {l.get('level', 0):.2f} | "
          f"3M trend: {l.get('trend_3m', 0):+.2f} | "
          f"Consec. declines: {l.get('consecutive_declines', 0)}")
    print("=" * 50)


if __name__ == "__main__":
    import time
    print("Fetching macro signals...")
    t = time.time()
    signals, vector = get_all_macro_signals(verbose=True)
    print(f"\nFetch time: {time.time()-t:.2f}s")
    print(f"Feature vector: {vector.shape} → {vector}")
