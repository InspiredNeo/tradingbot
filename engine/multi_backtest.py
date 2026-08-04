"""
Multi-configuration backtest engine.
Tests multiple bot configurations over the same historical period
and ranks them by risk-adjusted performance.
"""

import os
import sys
import json
import time
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from itertools import product

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
CONFIG   = os.path.expanduser("~/tradingbot/config")

# ── Universe definitions ──────────────────────────────────────
UNIVERSES = {
    "full": {
        "risk":      ["VTI","SCHF","QQQ","EEM","XLV","XLF"],
        "defensive": ["AGG","TLT","GLD"],
    },
    "equity": {
        "risk":      ["VTI","QQQ","EEM","XLV","XLF","SCHF"],
        "defensive": ["GLD"],          # only gold, no bonds
    },
    "defensive": {
        "risk":      ["VTI","SCHF","XLV"],
        "defensive": ["AGG","TLT","GLD","VNQ"],
    },
    "momentum": {
        "risk":      ["QQQ","VTI","XLV","XLF","EEM"],
        "defensive": ["GLD","TLT"],
    },
}

ETF_INCEPTION = {
    "VTI":"2001-06-15","SCHF":"2009-11-03","QQQ":"1999-03-10",
    "EEM":"2003-04-11","XLV":"1998-12-22","XLF":"1998-12-22",
    "AGG":"2003-09-29","TLT":"2002-07-26","GLD":"2004-11-18",
    "VNQ":"2004-10-01",
}

# ── Model blend definitions ───────────────────────────────────
BLENDS = {
    "current": {
        "risk_parity":0.35,"min_variance":0.20,
        "max_divers":0.15,"equal_weight":0.15,"bl_equilibrium":0.15
    },
    "momentum_heavy": {
        "risk_parity":0.15,"min_variance":0.10,
        "max_divers":0.10,"equal_weight":0.10,
        "bl_equilibrium":0.10,"momentum":0.45
    },
    "min_var_heavy": {
        "risk_parity":0.20,"min_variance":0.45,
        "max_divers":0.15,"equal_weight":0.10,"bl_equilibrium":0.10
    },
    "risk_parity_heavy": {
        "risk_parity":0.55,"min_variance":0.15,
        "max_divers":0.15,"equal_weight":0.10,"bl_equilibrium":0.05
    },
    "equal_blend": {
        "risk_parity":0.20,"min_variance":0.20,
        "max_divers":0.20,"equal_weight":0.20,"bl_equilibrium":0.20
    },
}

# ── Configurations to test ────────────────────────────────────
CONFIGS = [
    ("Pure Momentum", 0.95, 0.80, "momentum_heavy", "equity"),
]

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

TCOST = 0.0005
SVI_STEPS = 1000    # faster than production for backtesting
SVI_DRAWS  = 1000
OPT_DRAWS  = 100
LOOKBACK   = 504


def momentum_model(cov, returns, lookback=126):
    """6-month momentum, inverse-vol weighted."""
    from portfolio_engine import _project_simplex_capped
    if len(returns) < lookback:
        return np.ones(cov.shape[0]) / cov.shape[0]
    mom = returns.iloc[-lookback:].mean().values
    vols = returns.std().values
    scores = np.where(vols > 0, mom / vols, 0).clip(min=0)
    if scores.sum() == 0:
        return np.ones(len(scores)) / len(scores)
    w = scores / scores.sum()
    return _project_simplex_capped(w)


def run_single_config(name, risk_target, dial_floor,
                      blend_name, universe_name,
                      start="2004-06-30", verbose=True):
    """Run one configuration backtest."""
    from svi_covariance import fit_svi
    from stability_index import risk_multiplier, compute_components, compute_dial
    from portfolio_engine import (risk_parity, min_variance,
                                   max_diversification, equal_weight,
                                   bl_equilibrium, _project_simplex_capped)

    univ = UNIVERSES[universe_name]
    blend = BLENDS[blend_name]
    risk_assets = univ["risk"]
    def_assets  = univ["defensive"]
    all_assets  = risk_assets + def_assets

    # Load prices
    px_path = os.path.join(DATA_DIR, "bt_prices.parquet")
    if os.path.exists(px_path):
        px = pd.read_parquet(px_path)
    else:
        px = yf.download(all_assets + ["SPY"], start="2000-01-01",
                        progress=False, auto_adjust=True)["Close"]
        px.index = pd.to_datetime(px.index).tz_localize(None)
        px.to_parquet(px_path)

    # Load stability
    stab = pd.read_parquet(os.path.join(DATA_DIR, "stability.parquet"))

    # Dates
    dates = pd.date_range(start=start, end=px.index.max(), freq="ME")
    dates = [px.index[px.index <= d].max() for d in dates]
    dates = [d for d in dates if pd.notna(d)]

    port_val = 10000.0
    weights  = None
    records  = []
    t0 = time.time()

    for i, d in enumerate(dates):
        avail = [t for t in all_assets
                 if t in px.columns and
                 pd.Timestamp(ETF_INCEPTION.get(t,"2000-01-01")) <= d]
        if len(avail) < 3:
            continue

        avail_risk = [t for t in risk_assets if t in avail]
        avail_def  = [t for t in def_assets  if t in avail]

        # Drop any tickers with insufficient history at this date
        hist = px.loc[:d, avail].dropna(how="all")
        valid = hist.dropna(axis=1, thresh=60).columns.tolist()
        avail = [t for t in avail if t in valid]
        avail_risk = [t for t in avail_risk if t in avail]
        avail_def  = [t for t in avail_def  if t in avail]
        hist = hist[avail].dropna(axis=1)
        avail = list(hist.columns)
        avail_risk = [t for t in avail_risk if t in avail]
        avail_def  = [t for t in avail_def  if t in avail]
        rets = hist.pct_change().dropna().iloc[-LOOKBACK:]
        if len(rets) < 60:
            continue

        # SVI covariance
        try:
            covs, _ = fit_svi(rets, n_steps=SVI_STEPS,
                              n_draws=SVI_DRAWS, verbose=False)
            idx = np.linspace(0, len(covs)-1, OPT_DRAWS).astype(int)
            covs_np = covs[idx].numpy() * 252
        except Exception:
            continue

        n = len(avail)
        mkt_w = np.ones(n) / n

        MODEL_FNS = {
            "risk_parity":    risk_parity,
            "min_variance":   min_variance,
            "max_divers":     max_diversification,
            "equal_weight":   equal_weight,
            "bl_equilibrium": None,
            "momentum":       None,
        }

        per_model = {}
        n = len(avail)
        fallback = np.ones(n) / n
        for mname, bwt in blend.items():
            if bwt == 0:
                continue
            try:
                if mname == "bl_equilibrium":
                    w_m = bl_equilibrium(covs_np.mean(0), mkt_w)
                elif mname == "momentum":
                    w_m = momentum_model(covs_np.mean(0), rets)
                else:
                    fn = MODEL_FNS[mname]
                    ws = np.stack([fn(c) for c in covs_np])
                    w_m = ws.mean(0)
                if np.isnan(w_m).any() or w_m.sum() == 0:
                    w_m = fallback.copy()
            except Exception:
                w_m = fallback.copy()
            per_model[mname] = w_m

        w = sum(per_model[m]*blend[m]
                for m in blend if m in per_model and blend[m]>0)
        if np.isnan(w).any() or w.sum() == 0:
            w = fallback.copy()
        else:
            w = _project_simplex_capped(w)
        w = _project_simplex_capped(w)

        # Risk tolerance
        ri = [avail.index(t) for t in avail_risk if t in avail]
        di = [avail.index(t) for t in avail_def  if t in avail]
        if ri and di:
            cr = w[ri].sum()
            if cr > 0:
                w[ri] *= risk_target / cr
                w[di] *= (1-risk_target) / max(1-cr, 1e-9)
            w = w / w.sum()

        # Dial scaling
        dial_val = float(stab["stability_risk"].loc[:d].dropna().iloc[-1]) \
                   if len(stab["stability_risk"].loc[:d].dropna()) > 0 else 0.4
        mult = max(risk_multiplier(dial_val),
                   dial_floor / max(risk_target, 0.01))
        if ri and di:
            freed = w[ri].sum() * (1-mult)
            w[ri] *= mult
            if di:
                w[di] += freed*(w[di]/max(w[di].sum(),1e-9))
        w = _project_simplex_capped(w)

        # Transaction costs
        if weights is not None:
            old = weights.reindex(pd.Index(avail)).fillna(0).values
            turnover = np.abs(w - old[:len(w)]).sum() / 2
            port_val *= (1 - TCOST * turnover * 2)
        weights = pd.Series(w, index=avail)

        # Roll forward
        next_d = dates[i+1] if i+1 < len(dates) else px.index[-1]
        pp = px.loc[d:next_d, avail].dropna(how="all")
        if len(pp) < 2:
            continue
        pr = (pp.iloc[-1]/pp.iloc[0]-1)
        pr_aligned = pr.reindex(avail).fillna(0).values
        if np.any(np.isnan(pr_aligned)) or np.isnan(w).any():
            continue
        ret = (w * pr_aligned).sum()
        if np.isnan(ret) or np.isinf(ret):
            continue
        port_val *= (1+ret)
        records.append({"date": next_d, "portfolio": port_val,
                        "dial": dial_val})

        if verbose:
            elapsed = time.time()-t0
            eta = elapsed/(i+1)*(len(dates)-i-1) if i>0 else 0
            pct = (i+1)/len(dates)*100
            bar = "#"*int(pct/2) + "-"*(50-int(pct/2))
            print(f"  [{bar}] {pct:5.1f}%  {d.date()}  "
                  f"${port_val:>9,.0f}  dial={dial_val:.2f}  "
                  f"ETA={eta/60:.1f}m", flush=True)

    if not records:
        return None

    series = pd.Series([r["portfolio"] for r in records],
                       index=[r["date"] for r in records])

    # Metrics
    years = (series.index[-1]-series.index[0]).days/365.25
    total = series.iloc[-1]/10000-1
    ann   = (1+total)**(1/max(years,1))-1
    mrets = series.pct_change().dropna()
    sharpe = (mrets.mean()/mrets.std()*np.sqrt(12)) if mrets.std()>0 else 0
    roll_max = series.cummax()
    dd = (series-roll_max)/roll_max
    max_dd = float(dd.min())
    calmar = ann/max(abs(max_dd),1e-9)

    return {
        "name": name, "final": round(series.iloc[-1],0),
        "total": round(total*100,1), "ann_ret": round(ann*100,1),
        "sharpe": round(sharpe,2), "max_dd": round(max_dd*100,1),
        "calmar": round(calmar,2),
        "series": series,
    }


def run_all(start="2004-06-30"):
    print("="*72)
    print("MULTI-CONFIGURATION BACKTEST")
    print("="*72)
    print(f"Configs: {len(CONFIGS)}   Start: {start}")
    print(f"SVI: {SVI_STEPS} steps, {SVI_DRAWS} draws, {OPT_DRAWS} opt draws\n")

    results = []
    all_series = {}
    t0 = time.time()

    for i, (name, risk, floor, blend, univ) in enumerate(CONFIGS):
        print(f"[{i+1}/{len(CONFIGS)}] {name}")
        print(f"  risk={risk:.0%} floor={floor:.0%} "
              f"blend={blend} universe={univ}")
        try:
            r = run_single_config(name, risk, floor, blend, univ,
                                  start=start, verbose=True)
            if r:
                results.append(r)
                all_series[name] = r.pop("series")
                print(f"  → ${r['final']:,.0f}  {r['ann_ret']}% ann  "
                      f"Sharpe {r['sharpe']}  dd {r['max_dd']}%\n")
        except Exception as e:
            print(f"  FAILED: {e}\n")

    # Sort by Calmar (best risk-adjusted)
    results.sort(key=lambda x: x["calmar"], reverse=True)

    print("\n"+"="*72)
    print("RESULTS — ranked by Calmar ratio")
    print("="*72)
    print(f"\n  {'name':<22} {'$10k->':>10} {'total':>7} "
          f"{'ann':>7} {'sharpe':>7} {'max dd':>8} {'calmar':>8}")
    print("  "+"-"*72)
    for r in results:
        print(f"  {r['name']:<22} ${r['final']:>9,.0f} "
              f"{r['total']:>6.1f}% {r['ann_ret']:>6.1f}% "
              f"{r['sharpe']:>7.2f} {r['max_dd']:>7.1f}% "
              f"{r['calmar']:>8.2f}")

    # SPY benchmark
    spy_ann = 11.4
    spy_dd  = -50.8
    spy_cal = spy_ann/abs(spy_dd)
    print(f"\n  {'SPY benchmark':<22} ${'97,814':>9} "
          f"{'878.1':>6}% {'11.4':>6}% "
          f"{'2.14':>7} {'-50.8':>7}% {spy_cal:>8.2f}")

    # Save
    out = {"configs": results, "total_time": time.time()-t0}
    with open(os.path.join(DATA_DIR,"multi_backtest.json"),"w") as f:
        json.dump(out, f, indent=2, default=str)

    # Save series for charting
    series_out = {k: {"dates":[d.strftime("%Y-%m") for d in v.index],
                      "values":[round(float(x),2) for x in v.values]}
                  for k,v in all_series.items()}
    with open(os.path.join(DATA_DIR,"multi_series.json"),"w") as f:
        json.dump(series_out, f, indent=2)

    print(f"\n  Total runtime: {(time.time()-t0)/60:.0f} minutes")
    print(f"  Results saved to histdata/multi_backtest.json")
    return results


if __name__ == "__main__":
    run_all()
