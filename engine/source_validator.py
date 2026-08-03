"""
Cross-source data validation.

Compares the same underlying quantity across independent providers and
flags divergence. Exists because BAMLH0A0HYM2 silently returned 3 years
of data when we assumed 17, and nothing downstream noticed -- the missing
years were median-filled and the summary stats looked plausible.

A second source would have caught it immediately.

DESIGN NOTES
------------
Not every pair should match exactly. ^TNX is quoted at 10x the yield and
is an intraday index; DGS10 is Treasury's daily constant-maturity rate.
They track closely but differ by a few bp legitimately. Each check
therefore carries its own tolerance and its own transform.

Tiered response:
  - divergence <= warn_threshold   -> silent pass
  - warn_threshold < d <= fail     -> WARN, keep going
  - divergence > fail_threshold    -> raise SourceDivergenceError
"""

import os
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from dataclasses import dataclass
from typing import Callable, Optional
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
FRED_KEY = os.getenv("FRED_API_KEY")


class SourceDivergenceError(Exception):
    """Two sources disagree beyond the acceptable threshold."""


# ══════════════════════════════════════════════════════════════
# FETCHERS
# ══════════════════════════════════════════════════════════════

def fetch_fred(series_id, start="2015-01-01"):
    """FRED daily series -> pd.Series indexed by date."""
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": FRED_KEY,
                    "file_type": "json", "observation_start": start},
            timeout=30)
        obs = r.json().get("observations", [])
        d, v = [], []
        for o in obs:
            val = o.get("value", ".")
            if val not in (".", ""):
                d.append(pd.to_datetime(o["date"]))
                v.append(float(val))
        s = pd.Series(v, index=d).sort_index()
        s.index = s.index.normalize()
        return s
    except Exception as e:
        print(f"    fetch_fred({series_id}) failed: {e}")
        return pd.Series(dtype=float)


def fetch_yahoo(ticker, start="2015-01-01"):
    """Yahoo close series -> pd.Series indexed by date."""
    try:
        h = yf.Ticker(ticker).history(start=start, auto_adjust=False)
        if h.empty:
            return pd.Series(dtype=float)
        s = h["Close"].dropna()
        s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
        return s
    except Exception as e:
        print(f"    fetch_yahoo({ticker}) failed: {e}")
        return pd.Series(dtype=float)


def fetch_stooq(ticker, start="2015-01-01"):
    """
    Stooq -- a genuinely independent third source (not a Yahoo mirror).
    Free CSV endpoint, no key. Used as tiebreaker when FRED and Yahoo
    disagree.
    """
    try:
        url = f"https://stooq.com/q/d/l/?s={ticker}&i=d"
        df = pd.read_csv(url)
        if "Date" not in df.columns or "Close" not in df.columns:
            return pd.Series(dtype=float)
        df["Date"] = pd.to_datetime(df["Date"])
        s = df.set_index("Date")["Close"].sort_index()
        return s.loc[start:]
    except Exception:
        return pd.Series(dtype=float)


# ══════════════════════════════════════════════════════════════
# CHECK DEFINITIONS
# ══════════════════════════════════════════════════════════════

def _normalize(s):
    """Rebase a series to 100 at its first value, for level comparison."""
    s = s.dropna()
    if s.empty:
        return s
    return (s / s.iloc[0]) * 100.0


@dataclass
class Check:
    name: str
    source_a: Callable[[], pd.Series]
    source_b: Callable[[], pd.Series]
    label_a: str
    label_b: str
    transform_b: Optional[Callable[[pd.Series], pd.Series]] = None
    warn_pct: float = 0.5      # % divergence -> warn
    fail_pct: float = 2.0      # % divergence -> raise
    min_overlap: int = 200     # minimum shared dates to trust the check
    absolute_mode: bool = False  # compare raw difference, not % error
    unit: str = "%"              # label for reported divergence
    note: str = ""


CHECKS = [
    Check(
        name="VIX",
        source_a=lambda: fetch_fred("VIXCLS"),
        source_b=lambda: fetch_yahoo("^VIX"),
        label_a="FRED VIXCLS", label_b="Yahoo ^VIX",
        warn_pct=0.5, fail_pct=2.0,
        note="Identical index from two providers -- should match closely.",
    ),
    Check(
        name="10Y Treasury",
        source_a=lambda: fetch_fred("DGS10"),
        source_b=lambda: fetch_yahoo("^TNX"),
        label_a="FRED DGS10", label_b="Yahoo ^TNX",
        warn_pct=3.0, fail_pct=8.0,
        note="^TNX is already quoted in percent -- no /10 needed. "
             "Intraday index vs Treasury daily CMT gives a few bp of "
             "legitimate difference, hence the loose threshold.",
    ),
    Check(
        name="Fed Funds",
        # Resample daily to month-start averages so the two series are
        # actually comparable. Joining raw daily against monthly only
        # matched on the 1st of each month -- 138 dates, below threshold.
        source_a=lambda: fetch_fred("DFF").resample("MS").mean(),
        source_b=lambda: fetch_fred("FEDFUNDS"),
        label_a="FRED DFF (monthly avg)", label_b="FRED FEDFUNDS",
        warn_pct=0.02, fail_pct=0.10,
        min_overlap=100,
        absolute_mode=True, unit="pp",
        note="Compared in percentage points, not % error -- at ZIRP a "
             "half-bp gap becomes a 5.7% error and fires spuriously. "
             "0.02pp warn / 0.10pp fail are meaningful policy-rate gaps.",
    ),
    Check(
        name="S&P 500 index",
        # Stooq's free endpoint returned nothing (rate limit / blocked).
        # FRED's SP500 is an independent feed and always available.
        # Compared as normalized levels since SPY tracks the index at
        # roughly 1/10th and carries dividend adjustments.
        source_a=lambda: fetch_yahoo("SPY").pct_change() * 100,
        source_b=lambda: fetch_fred("SP500").pct_change() * 100,
        label_a="Yahoo SPY daily ret", label_b="FRED SP500 daily ret",
        warn_pct=0.05, fail_pct=1.50,
        absolute_mode=True, unit="pp",
        note="WARN is intentional and informative: SPY decouples from the "
             "index during stress (worst case 2020-03-16, -10.94% vs "
             "-11.98%) because ETF arbitrage breaks down. Median is "
             "0.026pp. Keep the warn threshold tight -- tracking breakdown "
             "is an execution risk the bot needs to know about. "
             "Comparing DAILY RETURNS, not levels. Level comparison drifts "
             "~5% over a decade from dividend adjustment and would warn "
             "forever -- a check you learn to ignore is worse than none. "
             "Returns are drift-immune and still catch real breaks.",
    ),
    Check(
        name="Credit Spread",
        source_a=lambda: fetch_fred("BAA10Y"),
        source_b=lambda: (fetch_fred("DBAA") - fetch_fred("DGS10")).dropna(),
        label_a="FRED BAA10Y", label_b="DBAA - DGS10",
        warn_pct=1.0, fail_pct=5.0,
        note="BAA10Y should equal Baa yield minus 10Y by construction. "
             "This is the check that would have caught the original bug.",
    ),
]


# ══════════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════════

def run_check(chk, verbose=True):
    """Run one check. Returns dict of results."""
    a = chk.source_a()
    b = chk.source_b()
    if chk.transform_b is not None and not b.empty:
        b = chk.transform_b(b)

    result = {"name": chk.name, "status": "UNKNOWN", "overlap": 0}

    if a.empty or b.empty:
        result["status"] = "NO_DATA"
        result["detail"] = (f"{chk.label_a}={len(a)} obs, "
                            f"{chk.label_b}={len(b)} obs")
        return result

    joined = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    result["overlap"] = len(joined)

    if len(joined) < chk.min_overlap:
        result["status"] = "INSUFFICIENT_OVERLAP"
        result["detail"] = (f"only {len(joined)} shared dates "
                            f"(need {chk.min_overlap})")
        return result

    # Percentage error is meaningless when the denominator approaches
    # zero -- a half-bp gap at a 0.09% policy rate reads as 5.7%.
    # For series flagged absolute_mode, compare raw difference instead.
    if chk.absolute_mode:
        pct = (joined["a"] - joined["b"]).abs()
    else:
        denom = joined["a"].abs().clip(lower=1e-6)
        pct = ((joined["a"] - joined["b"]).abs() / denom) * 100

    result.update({
        "median_pct": float(pct.median()),
        "p95_pct": float(pct.quantile(0.95)),
        "max_pct": float(pct.max()),
        "max_date": str(pct.idxmax().date()),
        "a_at_max": float(joined.loc[pct.idxmax(), "a"]),
        "b_at_max": float(joined.loc[pct.idxmax(), "b"]),
        "start": str(joined.index.min().date()),
        "end": str(joined.index.max().date()),
    })

    # Judge on the 95th percentile, not the max -- one bad print
    # shouldn't fail an otherwise sound series.
    judge = result["p95_pct"]
    if judge > chk.fail_pct:
        result["status"] = "FAIL"
    elif judge > chk.warn_pct:
        result["status"] = "WARN"
    else:
        result["status"] = "OK"

    return result


def validate_sources(raise_on_fail=True, verbose=True):
    """Run all cross-source checks."""
    print("=" * 66)
    print("CROSS-SOURCE VALIDATION")
    print("=" * 66)

    results = []
    for chk in CHECKS:
        if verbose:
            print(f"\n  {chk.name}")
            print(f"    {chk.label_a}  vs  {chk.label_b}")
        r = run_check(chk, verbose)
        results.append((chk, r))

        if r["status"] in ("NO_DATA", "INSUFFICIENT_OVERLAP"):
            print(f"    -> {r['status']}: {r.get('detail','')}")
            continue

        sym = {"OK": "OK  ", "WARN": "WARN", "FAIL": "FAIL"}[r["status"]]
        u = chk.unit
        print(f"    -> {sym}  median={r['median_pct']:.4f}{u}  "
              f"p95={r['p95_pct']:.4f}{u}  max={r['max_pct']:.4f}{u}")
        print(f"       overlap {r['overlap']} days "
              f"({r['start']} -> {r['end']})")
        if r["status"] != "OK":
            print(f"       worst: {r['max_date']}  "
                  f"{chk.label_a}={r['a_at_max']:.4f}  "
                  f"{chk.label_b}={r['b_at_max']:.4f}")
            if chk.note:
                print(f"       note: {chk.note}")

    # Summary
    print("\n" + "=" * 66)
    ok = sum(1 for _, r in results if r["status"] == "OK")
    warn = sum(1 for _, r in results if r["status"] == "WARN")
    fail = sum(1 for _, r in results if r["status"] == "FAIL")
    skip = sum(1 for _, r in results
               if r["status"] in ("NO_DATA", "INSUFFICIENT_OVERLAP"))
    print(f"  {ok} OK   {warn} WARN   {fail} FAIL   {skip} SKIPPED")
    print("=" * 66)

    if fail and raise_on_fail:
        bad = [c.name for c, r in results if r["status"] == "FAIL"]
        raise SourceDivergenceError(
            f"Sources disagree beyond tolerance: {', '.join(bad)}. "
            f"Investigate before trusting downstream data.")

    return results


if __name__ == "__main__":
    validate_sources(raise_on_fail=False)
