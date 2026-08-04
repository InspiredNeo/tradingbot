"""
Full system backtest: dial + SVI engine, 2004-2026.

HONESTY CONSTRAINTS
-------------------
1. No ETF used before its inception date.
2. SVI guide refit on trailing data at each rebalance -- no future
   covariance structure leaks into past allocations.
3. Transaction costs: 0.05% per trade (round-trip bid-ask proxy).
4. Benchmarks: SPY, 60/40 (SPY+AGG), VTI+SCHF (your holdings).
5. All four metrics reported regardless of outcome.
6. Time window: 2004-01-30 to present. Includes 2008, 2020, 2022.
   Not negotiable.

KNOWN LIMITATIONS (documented, not papered over)
-------------------------------------------------
- SVI guide certified on current data; refitting per period is honest
  but the guide architecture may not be equally expressive in all
  market regimes.
- ETF universe is survivorship-biased (all tickers exist today).
  Mitigated by using large liquid funds; material for small ETFs.
- Monthly rebalance only; intra-month moves not captured.
"""

import os
import sys
import time
import json
import warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
CONFIG   = os.path.expanduser("~/tradingbot/config")

# ── Universe with inception dates ────────────────────────────
ETF_INCEPTION = {
    "VTI":  "2001-06-15", "SCHF": "2009-11-03",
    "QQQ":  "1999-03-10", "EEM":  "2003-04-11",
    "XLV":  "1998-12-22", "XLF":  "1998-12-22",
    "AGG":  "2003-09-29", "TLT":  "2002-07-26",
    "GLD":  "2004-11-18",
}
RISK_ASSETS = ["VTI", "SCHF", "QQQ", "EEM", "XLV", "XLF"]
DEFENSIVE   = ["AGG", "TLT", "GLD"]
UNIVERSE    = RISK_ASSETS + DEFENSIVE

RISK_TARGETS   = {1: 0.35, 2: 0.50, 3: 0.62, 4: 0.75, 5: 0.88}
MAX_WEIGHT     = 0.40
LOOKBACK_DAYS  = 504      # 2yr trailing for covariance
SVI_STEPS      = 1500     # fewer than production -- converges by 500
SVI_DRAWS      = 2000     # enough for weight stability
def annualized_sharpe(series, freq="monthly"):
    """
    Correct Sharpe ratio annualization.
    freq: 'daily' uses sqrt(252), 'monthly' uses sqrt(12), 'weekly' uses sqrt(52)
    """
    import numpy as np
    rets = series.pct_change().dropna()
    if rets.std() == 0:
        return 0.0
    factors = {"daily": 252, "monthly": 12, "weekly": 52}
    factor = factors.get(freq, 12)
    return float((rets.mean() / rets.std()) * np.sqrt(factor))

TCOST_RT       = 0.0005   # 5bp round-trip


# ══════════════════════════════════════════════════════════════
# DATA PREP
# ══════════════════════════════════════════════════════════════

def load_prices():
    path = os.path.join(DATA_DIR, "bt_prices.parquet")
    if os.path.exists(path):
        return pd.read_parquet(path)
    print("  Downloading backtest price history...")
    px = yf.download(UNIVERSE + ["SPY"], start="2000-01-01",
                     progress=False, auto_adjust=True)["Close"]
    px.index = pd.to_datetime(px.index).tz_localize(None).normalize()
    px.to_parquet(path)
    return px


def available_universe(date):
    """ETFs with inception date <= date."""
    return [t for t in UNIVERSE
            if pd.Timestamp(ETF_INCEPTION[t]) <= pd.Timestamp(date)]


# ══════════════════════════════════════════════════════════════
# ALLOCATION AT A SINGLE DATE
# ══════════════════════════════════════════════════════════════

def allocate_at(date, px_history, tolerance=4, dial_value=None):
    """
    Compute target weights as of `date` using only px_history up to
    that date. Returns weight series indexed by UNIVERSE.
    """
    from svi_covariance import fit_svi
    from stability_index import risk_multiplier

    avail = available_universe(date)
    if len(avail) < 3:
        return pd.Series(1.0 / len(avail),
                         index=avail) if avail else pd.Series()

    # Trailing returns
    hist = px_history.loc[:date, avail].dropna(how="all")
    rets = hist.pct_change().dropna()
    if len(rets) < 60:
        # Not enough history -- equal weight
        return pd.Series(1.0 / len(avail), index=avail)

    rets = rets.iloc[-LOOKBACK_DAYS:]

    # Covariance posterior
    covs, info = fit_svi(rets, n_steps=SVI_STEPS,
                         n_draws=SVI_DRAWS, verbose=False)
    covs_np = covs.numpy() * 252

    # Draw a subset for optimization
    idx = np.linspace(0, len(covs_np) - 1, 200).astype(int)
    covs_sub = covs_np[idx]

    # Models
    from portfolio_engine import (risk_parity, min_variance,
                                   max_diversification,
                                   equal_weight, bl_equilibrium,
                                   _project_simplex_capped,
                                   MODEL_BLEND)
    n = len(avail)

    # Market cap proxy (equal for simplicity in backtest --
    # historical AUM unavailable without a data license)
    mkt_w = np.ones(n) / n

    per_model = {}
    for name in MODEL_BLEND:
        if name == "bl_equilibrium":
            per_model[name] = bl_equilibrium(covs_sub.mean(0), mkt_w)
            continue
        fn = {"risk_parity": risk_parity,
              "min_variance": min_variance,
              "max_divers":   max_diversification,
              "equal_weight": equal_weight}[name]
        ws = np.stack([fn(c) for c in covs_sub])
        per_model[name] = ws.mean(0)

    w = sum(per_model[m] * MODEL_BLEND[m] for m in MODEL_BLEND)
    w = _project_simplex_capped(w)

    # Risk tolerance rescale
    risk_ix = [avail.index(t) for t in avail if t in RISK_ASSETS]
    def_ix  = [avail.index(t) for t in avail if t in DEFENSIVE]
    target  = RISK_TARGETS.get(tolerance, 0.62)
    cur_r   = w[risk_ix].sum()
    if cur_r > 0 and len(def_ix) > 0:
        w[risk_ix] *= target / cur_r
        w[def_ix]  *= (1 - target) / max(1 - cur_r, 1e-9)
        w = w / w.sum()

    # Dial scaling
    if dial_value is not None:
        mult = risk_multiplier(dial_value)
        freed = w[risk_ix].sum() * (1 - mult)
        w[risk_ix] *= mult
        if len(def_ix) > 0:
            w[def_ix] += freed * (w[def_ix] / max(w[def_ix].sum(), 1e-9))
        w = w / w.sum()

    w = _project_simplex_capped(w)
    return pd.Series(w, index=avail)


# ══════════════════════════════════════════════════════════════
# BACKTEST LOOP
# ══════════════════════════════════════════════════════════════

def run_backtest(start="2004-06-30", tolerance=4, verbose=True):
    print("=" * 66)
    print("BACKTEST: dial + SVI engine vs benchmarks")
    print("=" * 66)
    print(f"  Start: {start}   Tolerance: {tolerance}/5")
    print(f"  Costs: {TCOST_RT*100:.2f}% round-trip per trade")

    px = load_prices()
    stab = pd.read_parquet(os.path.join(DATA_DIR, "stability.parquet"))

    # Monthly rebalance dates
    dates = pd.date_range(start=start, end=px.index.max(), freq="ME")
    dates = [px.index[px.index <= d].max() for d in dates]
    dates = [d for d in dates if pd.notna(d)]

    print(f"\n  Rebalance dates: {len(dates)} "
          f"({dates[0].date()} -> {dates[-1].date()})")
    print(f"  SVI: {SVI_STEPS} steps, {SVI_DRAWS} draws per rebalance\n")

    # -- main loop --
    portfolio_val = 10000.0
    weights = None
    records = []
    t0 = time.time()

    for i, d in enumerate(dates):
        # Get dial value for this date
        dial = float(stab["stability_risk"].loc[:d].dropna().iloc[-1]) \
               if d in stab.index or d > stab.index.min() else None

        # Compute new weights
        new_w = allocate_at(d, px, tolerance=tolerance, dial_value=dial)
        if new_w.empty:
            continue

        # Transaction costs on turnover
        if weights is not None:
            old_aligned = weights.reindex(new_w.index).fillna(0)
            turnover = (new_w - old_aligned).abs().sum() / 2
            portfolio_val *= (1 - TCOST_RT * turnover * 2)

        weights = new_w

        # Roll forward to next rebalance
        next_d = dates[i + 1] if i + 1 < len(dates) else px.index[-1]
        period_px = px.loc[d:next_d, new_w.index].dropna(how="all")
        if len(period_px) < 2:
            continue
        period_ret = (period_px.iloc[-1] / period_px.iloc[0] - 1)
        port_ret = (new_w * period_ret.reindex(new_w.index).fillna(0)).sum()
        portfolio_val *= (1 + port_ret)

        records.append({
            "date": next_d,
            "portfolio": portfolio_val,
            "dial": dial,
            "weights": new_w.to_dict(),
        })

        if verbose:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (len(dates) - i - 1)
            pct = (i + 1) / len(dates) * 100
            bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
            print(f"  [{bar}] {pct:5.1f}%  {d.date()}  "
                  f"port=${portfolio_val:>9,.0f}  dial={dial:.2f}  "
                  f"ETA={eta/60:.1f}m", flush=True)

    results = pd.DataFrame(records).set_index("date")

    # -- benchmarks --
    def benchmark(tickers, weights_list, name):
        vals = [10000.0]
        w = np.array(weights_list)
        for i, d in enumerate(dates[:-1]):
            next_d = dates[i + 1]
            available = [t for t in tickers if t in px.columns]
            period_px = px.loc[d:next_d, available].dropna(how="all")
            if len(period_px) < 2:
                vals.append(vals[-1])
                continue
            rets = (period_px.iloc[-1] / period_px.iloc[0] - 1)
            ww = np.array([w[tickers.index(t)] for t in available])
            ww = ww / ww.sum()
            vals.append(vals[-1] * (1 + (ww * rets.values).sum()))
        return pd.Series(vals[1:], index=dates[1:], name=name)

    spy_b  = benchmark(["SPY"], [1.0], "SPY")
    b6040  = benchmark(["SPY", "AGG"], [0.6, 0.4], "60/40")
    yours  = benchmark(["VTI", "SCHF"], [0.8, 0.2], "VTI+SCHF")

    # -- metrics --
    def metrics(series, name):
        rets = series.pct_change().dropna()
        ann_ret = (series.iloc[-1] / series.iloc[0]) ** (
            252 / max(len(rets), 1)) - 1
        ann_vol = rets.std() * np.sqrt(252)
        sharpe  = ann_ret / max(ann_vol, 1e-9)
        roll_max = series.cummax()
        dd = (series - roll_max) / roll_max
        max_dd  = float(dd.min())
        calmar  = ann_ret / max(abs(max_dd), 1e-9)
        total   = series.iloc[-1] / series.iloc[0] - 1
        return {"name": name, "total": total, "ann_ret": ann_ret,
                "sharpe": sharpe, "max_dd": max_dd, "calmar": calmar,
                "final": series.iloc[-1]}

    port_series = results["portfolio"]
    all_metrics = [
        metrics(port_series, f"Bot (tol={tolerance})"),
        metrics(spy_b,  "SPY"),
        metrics(b6040,  "60/40"),
        metrics(yours,  "VTI+SCHF"),
    ]

    print("\n" + "=" * 66)
    print("RESULTS")
    print("=" * 66)
    print(f"\n  {'strategy':<18} {'total':>8} {'ann ret':>8} "
          f"{'sharpe':>8} {'max dd':>8} {'calmar':>8}")
    print("  " + "-" * 62)
    for m in all_metrics:
        print(f"  {m['name']:<18} {m['total']:>7.1%} {m['ann_ret']:>7.1%} "
              f"{m['sharpe']:>8.2f} {m['max_dd']:>7.1%} "
              f"{m['calmar']:>8.2f}")

    # Save
    out = {
        "metrics": all_metrics,
        "start": str(dates[0].date()),
        "end": str(dates[-1].date()),
        "n_rebalances": len(records),
        "tolerance": tolerance,
    }
    with open(os.path.join(DATA_DIR, "backtest_results.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)

    pd.DataFrame({"portfolio": port_series}).to_parquet(
        os.path.join(DATA_DIR, "backtest_portfolio.parquet"))
    print(f"\n  Saved -> {DATA_DIR}/backtest_results.json")
    print(f"  Total runtime: {(time.time()-t0)/60:.1f} minutes")
    return results, all_metrics


if __name__ == "__main__":
    import sys
    tol = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    run_backtest(tolerance=tol)
