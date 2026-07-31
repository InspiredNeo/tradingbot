"""
Market Signals for Market Terminal Bot Engine.
Fetches and computes 10 core market signals.

Signals:
1.  VIX level
2.  VIX term structure (VIX9D vs VIX3M — fear curve shape)
3.  Yield curve 2Y-10Y spread
4.  Yield curve 3M-10Y spread
5.  Yield curve 5Y-30Y spread
6.  Credit spread (HYG vs LQD — high yield vs investment grade)
7.  Dollar index momentum (DXY)
8.  Gold momentum
9.  Oil momentum
10. Copper momentum (leading economic indicator)
"""

import os
import time
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
FRED_KEY = os.getenv("FRED_API_KEY")

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


def _fetch_fred(series_id, periods=252):
    """Fetch FRED series, return pandas Series."""
    try:
        resp = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": FRED_KEY,
                    "file_type": "json", "sort_order": "desc",
                    "limit": periods},
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


def _fetch_price(ticker, period="1y"):
    """Fetch price history via yfinance."""
    try:
        hist = yf.Ticker(ticker).history(period=period)
        return hist["Close"].dropna()
    except Exception:
        return pd.Series(dtype=float)


def _momentum(series, lookback=20):
    """Simple momentum: current vs N days ago, normalized."""
    if len(series) < lookback + 1:
        return 0.0
    current = series.iloc[-1]
    past = series.iloc[-lookback - 1]
    return (current - past) / past if past != 0 else 0.0


def _zscore(series, window=252):
    """Z-score of latest value vs rolling window."""
    if len(series) < 10:
        return 0.0
    recent = series.iloc[-min(window, len(series)):]
    mu = recent.mean()
    sigma = recent.std()
    if sigma == 0:
        return 0.0
    return float((series.iloc[-1] - mu) / sigma)


# ── Individual signal functions ────────────────────────────────

def get_vix_level():
    """
    VIX level and z-score.
    High VIX = fear/volatility. Low VIX = complacency.
    Returns: (vix_level, vix_zscore)
    """
    def _fetch():
        vix = _fetch_price("^VIX", period="2y")
        if vix.empty:
            return {"level": 20.0, "zscore": 0.0, "signal": "neutral"}
        level = float(vix.iloc[-1])
        zscore = _zscore(vix)
        # Signal interpretation
        if level > 30:
            signal = "crisis"
        elif level > 20:
            signal = "elevated"
        elif level < 12:
            signal = "complacent"
        else:
            signal = "normal"
        return {"level": level, "zscore": zscore, "signal": signal}
    return _cached("vix_level", _fetch)


def get_vix_term_structure():
    """
    VIX term structure: VIX9D vs VIX3M.
    Normal: short-term VIX < long-term (upward sloping = calm)
    Inverted: short-term VIX > long-term (downward sloping = acute fear)
    Returns: spread and shape
    """
    def _fetch():
        vix9d = _fetch_price("^VIX9D", period="6mo")
        vix3m = _fetch_price("^VIX3M", period="6mo")
        if vix9d.empty or vix3m.empty:
            return {"spread": 0.0, "inverted": False, "signal": "neutral"}
        spread = float(vix3m.iloc[-1]) - float(vix9d.iloc[-1])
        inverted = spread < 0
        return {
            "vix9d": float(vix9d.iloc[-1]),
            "vix3m": float(vix3m.iloc[-1]),
            "spread": spread,
            "inverted": inverted,
            "signal": "fear" if inverted else "calm",
        }
    return _cached("vix_term", _fetch)


def get_yield_curve():
    """
    Three yield curve spreads.
    Inversion = recession signal (historically very reliable).
    Returns: dict of spreads and inversion status.
    """
    def _fetch():
        # FRED series
        y2 = _fetch_fred("DGS2", 252)
        y10 = _fetch_fred("DGS10", 252)
        y3m = _fetch_fred("DGS3MO", 252)
        y30 = _fetch_fred("DGS30", 252)

        def spread(long, short):
            if long.empty or short.empty:
                return 0.0
            # Align on common dates
            combined = pd.concat([long, short], axis=1).dropna()
            if combined.empty:
                return 0.0
            return float(combined.iloc[-1, 0] - combined.iloc[-1, 1])

        s_2_10 = spread(y10, y2)
        s_3m_10 = spread(y10, y3m)
        s_5_30 = spread(y30, _fetch_fred("DGS5", 252))

        # Inversion count (more inversions = stronger recession signal)
        inversions = sum([s_2_10 < 0, s_3m_10 < 0, s_5_30 < 0])

        return {
            "spread_2_10": s_2_10,
            "spread_3m_10": s_3m_10,
            "spread_5_30": s_5_30,
            "inversions": inversions,
            "signal": "recession_warning" if inversions >= 2
                      else "caution" if inversions == 1
                      else "normal",
        }
    return _cached("yield_curve", _fetch)


def get_credit_spreads():
    """
    Credit spread: HYG (high yield) vs LQD (investment grade).
    Wide spread = credit stress = risk-off signal.
    """
    def _fetch():
        hyg = _fetch_price("HYG", period="2y")
        lqd = _fetch_price("LQD", period="2y")
        if hyg.empty or lqd.empty:
            return {"spread_momentum": 0.0, "signal": "neutral"}

        # Ratio of HYG to LQD (spread proxy)
        combined = pd.concat([hyg, lqd], axis=1).dropna()
        combined.columns = ["hyg", "lqd"]
        ratio = combined["hyg"] / combined["lqd"]

        momentum_1m = _momentum(ratio, 20)
        momentum_3m = _momentum(ratio, 60)
        zscore = _zscore(ratio)

        # Falling ratio = widening credit spreads = stress
        signal = "stress" if zscore < -1.5 else \
                 "caution" if zscore < -0.5 else \
                 "normal" if zscore < 0.5 else "tight"

        return {
            "ratio": float(ratio.iloc[-1]),
            "momentum_1m": momentum_1m,
            "momentum_3m": momentum_3m,
            "zscore": zscore,
            "signal": signal,
        }
    return _cached("credit_spreads", _fetch)


def get_dollar_momentum():
    """
    Dollar index (DXY) momentum.
    Strong dollar = headwind for international ETFs + commodities.
    """
    def _fetch():
        dxy = _fetch_price("DX-Y.NYB", period="1y")
        if dxy.empty:
            return {"momentum_1m": 0.0, "momentum_3m": 0.0,
                    "zscore": 0.0, "signal": "neutral"}
        m1 = _momentum(dxy, 20)
        m3 = _momentum(dxy, 60)
        z = _zscore(dxy)
        signal = "strong_dollar" if z > 1.5 else \
                 "weak_dollar" if z < -1.5 else "neutral"
        return {
            "level": float(dxy.iloc[-1]),
            "momentum_1m": m1,
            "momentum_3m": m3,
            "zscore": z,
            "signal": signal,
        }
    return _cached("dollar", _fetch)


def get_commodity_momentum():
    """
    Gold, Oil, Copper momentum.
    Gold up = risk-off / inflation hedge demand.
    Oil up = inflation pressure / growth signal.
    Copper up = global growth (copper is 'Dr. Copper' leading indicator).
    """
    def _fetch():
        tickers = {"gold": "GC=F", "oil": "CL=F", "copper": "HG=F"}
        result = {}
        for name, ticker in tickers.items():
            price = _fetch_price(ticker, period="1y")
            if price.empty:
                result[name] = {"momentum_1m": 0.0, "momentum_3m": 0.0,
                                "zscore": 0.0}
                continue
            result[name] = {
                "level": float(price.iloc[-1]),
                "momentum_1m": _momentum(price, 20),
                "momentum_3m": _momentum(price, 60),
                "zscore": _zscore(price),
            }
        # Composite signal
        copper_z = result.get("copper", {}).get("zscore", 0)
        gold_z = result.get("gold", {}).get("zscore", 0)
        oil_z = result.get("oil", {}).get("zscore", 0)

        # High copper + high oil = growth/inflation
        # High gold + low copper = fear/deflation
        if copper_z > 0.5 and oil_z > 0:
            composite = "growth"
        elif gold_z > 1.0 and copper_z < 0:
            composite = "fear"
        elif oil_z > 1.5:
            composite = "inflation"
        else:
            composite = "neutral"

        result["composite_signal"] = composite
        return result
    return _cached("commodities", _fetch)


# ── Master signal collector ────────────────────────────────────

def get_all_market_signals(verbose=False):
    """
    Fetch all 10 market signals in parallel.
    Returns normalized signal vector for regime detection.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    signal_fns = {
        "vix": get_vix_level,
        "vix_term": get_vix_term_structure,
        "yield_curve": get_yield_curve,
        "credit": get_credit_spreads,
        "dollar": get_dollar_momentum,
        "commodities": get_commodity_momentum,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
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

    # Build normalized feature vector for regime detection
    vector = _to_feature_vector(results)
    return results, vector


def _to_feature_vector(signals):
    """
    Convert signal dict to normalized numpy array.
    This is the input to the regime detection neural network.
    """
    vix = signals.get("vix", {})
    vix_term = signals.get("vix_term", {})
    yc = signals.get("yield_curve", {})
    credit = signals.get("credit", {})
    dollar = signals.get("dollar", {})
    commod = signals.get("commodities", {})

    vector = np.array([
        # VIX (2 features)
        np.clip(vix.get("zscore", 0), -3, 3),
        1.0 if vix.get("signal") == "crisis" else 0.0,

        # VIX term structure (2 features)
        np.clip(vix_term.get("spread", 0) / 5, -3, 3),
        1.0 if vix_term.get("inverted") else 0.0,

        # Yield curve (4 features)
        np.clip(yc.get("spread_2_10", 0) / 2, -3, 3),
        np.clip(yc.get("spread_3m_10", 0) / 2, -3, 3),
        np.clip(yc.get("spread_5_30", 0) / 2, -3, 3),
        float(yc.get("inversions", 0)) / 3,

        # Credit spreads (2 features)
        np.clip(credit.get("zscore", 0), -3, 3),
        np.clip(credit.get("momentum_1m", 0) * 10, -3, 3),

        # Dollar (2 features)
        np.clip(dollar.get("zscore", 0), -3, 3),
        np.clip(dollar.get("momentum_1m", 0) * 10, -3, 3),

        # Commodities (4 features)
        np.clip(commod.get("gold", {}).get("zscore", 0), -3, 3),
        np.clip(commod.get("oil", {}).get("zscore", 0), -3, 3),
        np.clip(commod.get("copper", {}).get("zscore", 0), -3, 3),
        np.clip(commod.get("copper", {}).get("momentum_1m", 0) * 10, -3, 3),
    ], dtype=np.float32)

    return vector  # 16 features from market signals


def _print_signals(signals):
    """Pretty print all signals."""
    print("\n" + "=" * 50)
    print("MARKET SIGNALS")
    print("=" * 50)

    vix = signals.get("vix", {})
    print(f"\nVIX: {vix.get('level', 'N/A'):.1f} "
          f"(z={vix.get('zscore', 0):.2f}) → {vix.get('signal', 'N/A').upper()}")

    vt = signals.get("vix_term", {})
    print(f"VIX Term: 9D={vt.get('vix9d', 'N/A'):.1f} "
          f"3M={vt.get('vix3m', 'N/A'):.1f} "
          f"spread={vt.get('spread', 0):.2f} "
          f"→ {'INVERTED ⚠️' if vt.get('inverted') else 'NORMAL'}")

    yc = signals.get("yield_curve", {})
    print(f"Yield Curve: 2-10={yc.get('spread_2_10', 0):.2f}% "
          f"3M-10={yc.get('spread_3m_10', 0):.2f}% "
          f"inversions={yc.get('inversions', 0)} "
          f"→ {yc.get('signal', 'N/A').upper()}")

    cr = signals.get("credit", {})
    print(f"Credit: z={cr.get('zscore', 0):.2f} "
          f"1m_mom={cr.get('momentum_1m', 0)*100:.1f}% "
          f"→ {cr.get('signal', 'N/A').upper()}")

    d = signals.get("dollar", {})
    print(f"Dollar: level={d.get('level', 'N/A'):.1f} "
          f"z={d.get('zscore', 0):.2f} "
          f"→ {d.get('signal', 'N/A').upper()}")

    c = signals.get("commodities", {})
    print(f"Commodities: gold_z={c.get('gold', {}).get('zscore', 0):.2f} "
          f"oil_z={c.get('oil', {}).get('zscore', 0):.2f} "
          f"copper_z={c.get('copper', {}).get('zscore', 0):.2f} "
          f"→ {c.get('composite_signal', 'N/A').upper()}")
    print("=" * 50)


if __name__ == "__main__":
    print("Fetching market signals...")
    import time
    t = time.time()
    signals, vector = get_all_market_signals(verbose=True)
    print(f"\nFetch time: {time.time()-t:.2f}s")
    print(f"Feature vector shape: {vector.shape}")
    print(f"Feature vector: {vector}")
