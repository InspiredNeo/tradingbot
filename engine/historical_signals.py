"""
Phase 4 (real) — Point-in-time historical signal reconstruction.

Builds signal vectors "as of" past dates using ONLY information that was
actually available on those dates. This is the training data for the
regime detector.

KEY DESIGN CONSTRAINTS
----------------------
1. No lookahead. For sample date D, every input is sliced to <= D, and
   lagged series are further restricted by their publication lag.
2. No revised macro where avoidable. Treasury rates, fed funds, and the
   ICE BofA HY OAS are never revised. CPI/unemployment are lightly
   revised -- included with lag, flagged as a known limitation.
   GDP / LEI / consumer confidence are DROPPED (heavy revision + long lag).
3. No late-inception ETFs. Requiring QUAL/MTUM/USMV/XLRE/XLC would push
   the start date to 2018 and leave us with one crisis example.

FEATURE COUNT: 30 (vs 58 live). The 12 sentiment features and 16 macro
features are not reconstructable; 14 macro-ish features survive as
market/rate features. See FEATURE_NAMES for the exact list.
"""

import os
import sys
import time
import json
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
FRED_KEY = os.getenv("FRED_API_KEY")

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
os.makedirs(DATA_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# DATA REGISTRY — inception dates and publication lags
# ══════════════════════════════════════════════════════════════

# Price series: ticker -> (label, first reliable date)
PRICE_SERIES = {
    # Volatility
    "^VIX":      ("vix",          "1990-01-02"),
    # Broad equity
    "SPY":       ("spy",          "1993-02-01"),
    "IWM":       ("small_cap",    "2000-06-01"),
    # International
    "EFA":       ("developed",    "2001-09-01"),
    "EEM":       ("emerging",     "2003-05-01"),
    "VGK":       ("europe",       "2005-04-01"),
    "VPL":       ("pacific",      "2005-04-01"),
    # Fixed income
    "AGG":       ("bonds_agg",    "2003-10-01"),
    "TLT":       ("bonds_long",   "2002-08-01"),
    # Alternatives
    "GLD":       ("gold_etf",     "2004-12-01"),
    "VNQ":       ("reits",        "2004-10-01"),
    # Style
    "VTV":       ("value",        "2004-02-01"),
    "VUG":       ("growth",       "2004-02-01"),
    # Sectors (SPDR, all launched Dec 1998)
    "XLK":       ("tech",         "1999-01-04"),
    "XLV":       ("health",       "1999-01-04"),
    "XLF":       ("financials",   "1999-01-04"),
    "XLE":       ("energy",       "1999-01-04"),
    "XLI":       ("industrials",  "1999-01-04"),
    "XLY":       ("cons_disc",    "1999-01-04"),
    "XLP":       ("cons_stap",    "1999-01-04"),
    "XLU":       ("utilities",    "1999-01-04"),
    "XLB":       ("materials",    "1999-01-04"),
    # Macro-ish market series
    "DX-Y.NYB":  ("dollar",       "2000-01-03"),
    "GC=F":      ("gold_fut",     "2000-08-30"),
    "CL=F":      ("oil",          "2000-08-23"),
    "HG=F":      ("copper",       "2000-08-30"),
}

# FRED series: id -> (label, first date, publication lag in days, revised?)
FRED_SERIES = {
    # --- Never revised, daily ---
    "DGS2":           ("y2",        "1976-06-01",  1, False),
    "DGS10":          ("y10",       "1962-01-02",  1, False),
    "DGS3MO":         ("y3m",       "1982-01-04",  1, False),
    "DGS5":           ("y5",        "1962-01-02",  1, False),
    "DGS30":          ("y30",       "1977-02-15",  1, False),
    "DFF":            ("fedfunds",  "1954-07-01",  1, False),
    "BAA10Y":         ("credit",    "1986-01-02",  1, False),
    # --- Lightly revised, monthly. Lag = worst-case publication delay ---
    "CPIAUCSL":       ("cpi",       "1947-01-01", 45, True),
    "UNRATE":         ("unrate",    "1948-01-01", 21, True),
}

# Explicitly dropped and why -- kept in code so the decision is auditable
DROPPED_SERIES = {
    "QUAL":    "inception 2013 -- would push start to post-2008",
    "MTUM":    "inception 2013 -- would push start to post-2008",
    "USMV":    "inception 2011 -- would push start to post-2008",
    "XLRE":    "inception 2015 -- would push start past 2008",
    "XLC":     "inception 2018 -- would leave only 2020 as a crisis",
    "VXUS":    "inception 2011 -- EFA used instead",
    "HYG":     "inception 2007 -- too short, misses most of 2008",
    "BAMLH0A0HYM2": ("FRED re-versioned the entire ICE BofA OAS family; "
                     "all IDs now start 2023-08-01. Replaced with BAA10Y "
                     "(Moody's Baa vs 10Y, daily, unrevised, since 1986). "
                     "Baa is investment-grade so less sensitive than HY OAS "
                     "-- ~6% peak in 2008 vs ~20% for HY -- but it actually "
                     "covers the period."),
    "^VIX9D":  "inception 2011 -- term structure dropped entirely",
    "^VIX3M":  "inception 2007 -- term structure dropped entirely",
    "GDP":     "quarterly, ~30d lag, heavily revised -- lookahead risk",
    "USSLIND": "revised; composite already contains our other inputs",
    "UMCSENT": "revised; survey data, weak point-in-time integrity",
    "ISM":     "not freely available on FRED; proxies were unreliable",
}


# ══════════════════════════════════════════════════════════════
# BULK DOWNLOAD (once) — everything cached to disk
# ══════════════════════════════════════════════════════════════

def download_price_history(force=False):
    """Download full price history for all tickers. Cached to parquet."""
    cache = os.path.join(DATA_DIR, "prices.parquet")
    if os.path.exists(cache) and not force:
        df = pd.read_parquet(cache)
        print(f"  Loaded cached prices: {df.shape[0]} days x "
              f"{df.shape[1]} series")
        return df

    print("  Downloading price history (this takes ~60s)...")
    tickers = list(PRICE_SERIES.keys())
    raw = yf.download(tickers, start="1990-01-01", progress=False,
                      auto_adjust=True)["Close"]

    # Rename to labels
    rename = {t: PRICE_SERIES[t][0] for t in tickers if t in raw.columns}
    df = raw.rename(columns=rename)

    # Normalize index to tz-naive dates
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df.sort_index()

    df.to_parquet(cache)
    print(f"  Downloaded: {df.shape[0]} days x {df.shape[1]} series")
    return df


FRED_REQUEST_START = "1990-01-01"   # what we ask FRED for


def download_fred_history(force=False):
    """Download full FRED history for all series. Cached to parquet."""
    cache = os.path.join(DATA_DIR, "fred.parquet")
    if os.path.exists(cache) and not force:
        df = pd.read_parquet(cache)
        print(f"  Loaded cached FRED: {df.shape[0]} obs x "
              f"{df.shape[1]} series")
        return df

    print("  Downloading FRED history...")
    frames = {}
    for series_id, (label, start, lag, revised) in FRED_SERIES.items():
        try:
            resp = requests.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": series_id, "api_key": FRED_KEY,
                        "file_type": "json", "observation_start": FRED_REQUEST_START},
                timeout=30,
            )
            obs = resp.json().get("observations", [])
            dates, vals = [], []
            for o in obs:
                v = o.get("value", ".")
                if v not in (".", ""):
                    dates.append(pd.to_datetime(o["date"]))
                    vals.append(float(v))
            frames[label] = pd.Series(vals, index=dates).sort_index()
            print(f"    {label:<10} {len(vals):>6} obs")
        except Exception as e:
            print(f"    {label:<10} FAILED: {e}")
            frames[label] = pd.Series(dtype=float)

    df = pd.DataFrame(frames).sort_index()
    df.index = pd.to_datetime(df.index).normalize()

    _validate_coverage(df)

    df.to_parquet(cache)
    print(f"  Downloaded: {df.shape[0]} obs x {df.shape[1]} series")
    return df


class DataCoverageError(Exception):
    """Raised when a series does not cover its claimed date range."""


def _validate_coverage(df, tolerance_days=400):
    """
    Verify every FRED series actually covers the start date claimed in
    FRED_SERIES. Raises rather than allowing silent fill.

    This exists because BAMLH0A0HYM2 was assumed to start in 1996, actually
    started 2023-08-01, and the missing 17 years were quietly median-filled
    into the training set. The stats looked plausible. Nothing crashed.
    """
    print("\n  Validating coverage...")
    failures = []
    for series_id, (label, claimed_start, lag, revised) in FRED_SERIES.items():
        if label not in df.columns:
            failures.append(f"{label}: column missing entirely")
            continue
        s = df[label].dropna()
        if s.empty:
            failures.append(f"{label}: no numeric observations")
            continue
        actual = s.index.min()
        # Expected start = later of (what the series has, what we asked for)
        expected = max(pd.Timestamp(claimed_start),
                       pd.Timestamp(FRED_REQUEST_START))
        gap = (actual - expected).days
        flag = "REVISED" if revised else ""
        if gap > tolerance_days:
            failures.append(
                f"{label} ({series_id}): expected data from "
                f"{expected.date()}, got {actual.date()} -- {gap} day gap, "
                f"only {len(s)} obs")
        else:
            print(f"    OK  {label:<10} {actual.date()} -> "
                  f"{s.index.max().date()}  {len(s):>6} obs  {flag}")

    # Independent check: monthly series need enough obs to be real.
    # This is what would have caught the 787-observation credit series.
    for series_id, (label, claimed_start, lag, revised) in FRED_SERIES.items():
        if label not in df.columns:
            continue
        s = df[label].dropna()
        if s.empty:
            continue
        span_years = (s.index.max() - s.index.min()).days / 365.25
        if span_years < 15:
            failures.append(
                f"{label} ({series_id}): only {span_years:.1f} years of "
                f"history ({len(s)} obs) -- too short to cover 2008")

    if failures:
        msg = ("\n  COVERAGE FAILURE -- refusing to build a dataset with "
               "fabricated history:\n")
        for f in failures:
            msg += f"    {f}\n"
        msg += ("\n  Fix the series ID or adjust its claimed start date in "
                "FRED_SERIES.\n  Do NOT lower the tolerance to make this "
                "pass.\n")
        raise DataCoverageError(msg)
    print("    All series cover their claimed ranges.")
    return True


# ══════════════════════════════════════════════════════════════
# POINT-IN-TIME SIGNAL COMPUTATION
# ══════════════════════════════════════════════════════════════

def _mom(s, days):
    """Momentum over `days` trading days. NaN if insufficient history."""
    s = s.dropna()
    if len(s) < days + 1:
        return np.nan
    return float(s.iloc[-1] / s.iloc[-days - 1] - 1.0)


def _zscore(s, window):
    """Z-score of last value vs trailing window."""
    s = s.dropna()
    if len(s) < max(20, window // 4):
        return np.nan
    w = s.iloc[-window:]
    mu, sd = w.mean(), w.std()
    if sd == 0 or np.isnan(sd):
        return np.nan
    return float((s.iloc[-1] - mu) / sd)


def _asof_fred(fred_df, label, date, lag_days):
    """
    Latest FRED value for `label` known as of `date`, respecting
    publication lag. Returns (value, series_up_to_cutoff).
    """
    if label not in fred_df.columns:
        return np.nan, pd.Series(dtype=float)
    cutoff = pd.Timestamp(date) - pd.Timedelta(days=lag_days)
    s = fred_df[label].loc[:cutoff].dropna()
    if s.empty:
        return np.nan, s
    return float(s.iloc[-1]), s


FEATURE_NAMES = [
    # --- Volatility (3) ---
    "vix_level_scaled", "vix_z_252", "vix_mom_21",
    # --- Yield curve (5) ---
    "spread_2_10", "spread_3m_10", "spread_5_30",
    "n_inversions", "y10_mom_63",
    # --- Credit (3) ---
    "credit_level", "credit_z_252", "credit_mom_63",
    # --- Policy / inflation (3) ---
    "fedfunds_vs_neutral", "fedfunds_mom_126", "cpi_yoy_lagged",
    # --- Labor (1) ---
    "unrate_mom_lagged",
    # --- Dollar & commodities (4) ---
    "dollar_z_252", "gold_mom_63", "oil_mom_63", "copper_mom_63",
    # --- Time-series momentum (4) ---
    "spy_mom_21", "spy_mom_63", "spy_mom_126", "spy_mom_252",
    # --- Cross-asset (3) ---
    "stock_bond_spread", "spy_vs_gold", "spy_vs_reits",
    # --- Sector rotation (2) ---
    "cyclical_vs_defensive", "sector_dispersion",
    # --- Style & breadth (2) ---
    "growth_vs_value", "smallcap_vs_large",
    # --- Geography (2) ---
    "us_vs_intl", "em_vs_developed",
    # --- Realized risk (1) ---
    "spy_realized_vol_63",
]
N_FEATURES = len(FEATURE_NAMES)   # 33

CYCLICAL = ["tech", "financials", "energy", "industrials", "cons_disc"]
DEFENSIVE = ["utilities", "cons_stap", "health"]
ALL_SECTORS = CYCLICAL + DEFENSIVE + ["materials"]


def compute_signals_asof(prices, fred, date):
    """
    Compute the point-in-time feature vector for a single date.
    Everything is sliced to <= date; FRED respects publication lag.
    Returns np.array of length N_FEATURES (may contain NaN).
    """
    date = pd.Timestamp(date)
    px = prices.loc[:date]
    f = np.full(N_FEATURES, np.nan, dtype=np.float64)
    i = 0

    def put(v):
        nonlocal i
        f[i] = v if v is not None else np.nan
        i += 1

    # --- Volatility (3) ---
    vix = px["vix"].dropna() if "vix" in px else pd.Series(dtype=float)
    put(float(vix.iloc[-1]) / 20.0 - 1.0 if len(vix) else np.nan)
    put(_zscore(vix, 252))
    put(_mom(vix, 21))

    # --- Yield curve (5) ---
    y2, _   = _asof_fred(fred, "y2",  date, 1)
    y10, s10 = _asof_fred(fred, "y10", date, 1)
    y3m, _  = _asof_fred(fred, "y3m", date, 1)
    y5, _   = _asof_fred(fred, "y5",  date, 1)
    y30, _  = _asof_fred(fred, "y30", date, 1)

    sp_2_10  = y10 - y2  if not (np.isnan(y10) or np.isnan(y2))  else np.nan
    sp_3m_10 = y10 - y3m if not (np.isnan(y10) or np.isnan(y3m)) else np.nan
    sp_5_30  = y30 - y5  if not (np.isnan(y30) or np.isnan(y5))  else np.nan
    put(sp_2_10)
    put(sp_3m_10)
    put(sp_5_30)
    inv = sum(1 for s in (sp_2_10, sp_3m_10, sp_5_30)
              if not np.isnan(s) and s < 0)
    put(float(inv))
    put(_mom(s10, 63) if len(s10) > 63 else np.nan)

    # --- Credit (3) ---
    # BAA10Y is Moody's Baa yield minus 10Y Treasury, in percentage points.
    # Level is already a spread, so no transform needed. Momentum is a
    # DIFFERENCE not a ratio -- a spread going 2% -> 4% is +2, not +100%.
    cr, s_cr = _asof_fred(fred, "credit", date, 1)
    put(cr)
    put(_zscore(s_cr, 252))
    s_cr_c = s_cr.dropna()
    put(float(s_cr_c.iloc[-1] - s_cr_c.iloc[-64])
        if len(s_cr_c) > 64 else np.nan)

    # --- Policy / inflation (3) ---
    ff, s_ff = _asof_fred(fred, "fedfunds", date, 1)
    put(ff - 2.75 if not np.isnan(ff) else np.nan)   # vs est. neutral r*
    put((s_ff.iloc[-1] - s_ff.iloc[-126]) if len(s_ff) > 126 else np.nan)

    _, s_cpi = _asof_fred(fred, "cpi", date, 45)
    put(float(s_cpi.iloc[-1] / s_cpi.iloc[-13] - 1) * 100
        if len(s_cpi) > 13 else np.nan)

    # --- Labor (1) ---
    _, s_un = _asof_fred(fred, "unrate", date, 21)
    put(float(s_un.iloc[-1] - s_un.iloc[-4]) if len(s_un) > 4 else np.nan)

    # --- Dollar & commodities (4) ---
    put(_zscore(px["dollar"], 252) if "dollar" in px else np.nan)
    put(_mom(px["gold_fut"], 63)   if "gold_fut" in px else np.nan)
    put(_mom(px["oil"], 63)        if "oil" in px else np.nan)
    put(_mom(px["copper"], 63)     if "copper" in px else np.nan)

    # --- Time-series momentum (4) ---
    spy = px["spy"].dropna() if "spy" in px else pd.Series(dtype=float)
    for d in (21, 63, 126, 252):
        put(_mom(spy, d))

    # --- Cross-asset (3) ---
    bond_mom = _mom(px["bonds_agg"], 63) if "bonds_agg" in px else np.nan
    spy_63 = _mom(spy, 63)
    put(spy_63 - bond_mom if not (np.isnan(spy_63) or np.isnan(bond_mom))
        else np.nan)
    gold_mom = _mom(px["gold_etf"], 63) if "gold_etf" in px else np.nan
    put(spy_63 - gold_mom if not (np.isnan(spy_63) or np.isnan(gold_mom))
        else np.nan)
    reit_mom = _mom(px["reits"], 63) if "reits" in px else np.nan
    put(spy_63 - reit_mom if not (np.isnan(spy_63) or np.isnan(reit_mom))
        else np.nan)

    # --- Sector rotation (2) ---
    cyc = [_mom(px[s], 63) for s in CYCLICAL if s in px]
    dfn = [_mom(px[s], 63) for s in DEFENSIVE if s in px]
    cyc = [x for x in cyc if not np.isnan(x)]
    dfn = [x for x in dfn if not np.isnan(x)]
    put(np.mean(cyc) - np.mean(dfn) if cyc and dfn else np.nan)
    allsec = [_mom(px[s], 63) for s in ALL_SECTORS if s in px]
    allsec = [x for x in allsec if not np.isnan(x)]
    put(float(np.std(allsec)) if len(allsec) >= 5 else np.nan)

    # --- Style & breadth (2) ---
    g = _mom(px["growth"], 63) if "growth" in px else np.nan
    v = _mom(px["value"], 63)  if "value" in px else np.nan
    put(g - v if not (np.isnan(g) or np.isnan(v)) else np.nan)
    sc = _mom(px["small_cap"], 63) if "small_cap" in px else np.nan
    put(sc - spy_63 if not (np.isnan(sc) or np.isnan(spy_63)) else np.nan)

    # --- Geography (2) ---
    dev = _mom(px["developed"], 63) if "developed" in px else np.nan
    put(spy_63 - dev if not (np.isnan(spy_63) or np.isnan(dev)) else np.nan)
    em = _mom(px["emerging"], 63) if "emerging" in px else np.nan
    put(em - dev if not (np.isnan(em) or np.isnan(dev)) else np.nan)

    # --- Realized risk (1) ---
    if len(spy) > 64:
        rets = spy.pct_change().dropna().iloc[-63:]
        put(float(rets.std() * np.sqrt(252)))
    else:
        put(np.nan)

    assert i == N_FEATURES, f"filled {i}, expected {N_FEATURES}"
    return f


# ══════════════════════════════════════════════════════════════
# DATASET BUILD
# ══════════════════════════════════════════════════════════════

def build_dataset(start="2005-06-30", end=None, freq="ME",
                  max_nan_frac=0.10, force_download=False):
    """
    Build the point-in-time feature matrix.

    freq: 'ME' month-end (~250 samples), 'W-FRI' weekly (~1100 but
          heavily autocorrelated -- effective sample size is far lower).
    max_nan_frac: drop sample dates where more than this fraction of
          features are NaN.
    """
    print("=" * 62)
    print("HISTORICAL SIGNAL RECONSTRUCTION")
    print("=" * 62)

    prices = download_price_history(force=force_download)
    fred = download_fred_history(force=force_download)

    if end is None:
        end = prices.index.max()
    dates = pd.date_range(start=start, end=end, freq=freq)
    # Snap each sample date back to the last available trading day
    trading = prices.index
    dates = [trading[trading <= d].max() for d in dates]
    dates = [d for d in dates if pd.notna(d)]
    dates = sorted(set(dates))

    print(f"\n  Sample dates: {len(dates)} "
          f"({dates[0].date()} -> {dates[-1].date()}, freq={freq})")
    print(f"  Features: {N_FEATURES}")
    print("\n  Computing point-in-time signals...")

    rows, kept_dates, dropped = [], [], 0
    t0 = time.time()
    for n, d in enumerate(dates):
        vec = compute_signals_asof(prices, fred, d)
        nan_frac = np.isnan(vec).mean()
        if nan_frac > max_nan_frac:
            dropped += 1
            continue
        rows.append(vec)
        kept_dates.append(d)
        if (n + 1) % 50 == 0:
            print(f"    {n+1}/{len(dates)} ... {time.time()-t0:.1f}s")

    X = np.array(rows)
    print(f"\n  Built: {X.shape[0]} samples x {X.shape[1]} features "
          f"in {time.time()-t0:.1f}s")
    print(f"  Dropped {dropped} dates (>{max_nan_frac:.0%} NaN)")

    # Per-feature NaN report -- this is where silent breakage shows up
    nan_by_feat = np.isnan(X).mean(axis=0)
    bad = [(FEATURE_NAMES[i], nan_by_feat[i])
           for i in range(N_FEATURES) if nan_by_feat[i] > 0.01]
    if bad:
        print("\n  Features with >1% NaN:")
        for name, frac in sorted(bad, key=lambda x: -x[1]):
            print(f"    {name:<24} {frac:6.1%}")
    else:
        print("\n  No feature exceeds 1% NaN.")

    # Forward-fill residual NaN along time, then median-fill any leader NaN
    Xdf = pd.DataFrame(X, index=kept_dates, columns=FEATURE_NAMES)
    Xdf = Xdf.ffill()
    Xdf = Xdf.fillna(Xdf.median())

    out = os.path.join(DATA_DIR, "features.parquet")
    Xdf.to_parquet(out)
    print(f"\n  Saved -> {out}")

    meta = {
        "n_samples": int(Xdf.shape[0]),
        "n_features": int(Xdf.shape[1]),
        "start": str(kept_dates[0].date()),
        "end": str(kept_dates[-1].date()),
        "freq": freq,
        "feature_names": FEATURE_NAMES,
        "dropped_series": DROPPED_SERIES,
        "known_limitations": [
            "CPI and unemployment are lightly revised; publication lag "
            "applied but revision bias remains.",
            "Sentiment features (news, insider, analyst, options) are not "
            "reconstructable and are absent from this feature set.",
            "Live signal code and historical signal code are separate "
            "implementations -- they must be checked for agreement.",
        ],
        "built": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(DATA_DIR, "features_meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)

    return Xdf


if __name__ == "__main__":
    Xdf = build_dataset(start="2005-06-30", freq="ME")
    print("\n" + "=" * 62)
    print("SAMPLE OUTPUT (last 3 dates, first 8 features)")
    print("=" * 62)
    print(Xdf.iloc[-3:, :8].round(3).to_string())
    print("\nFeature summary:")
    print(Xdf.describe().T[["mean", "std", "min", "max"]].round(3).to_string())
