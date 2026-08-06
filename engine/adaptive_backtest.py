"""
Phase 5.5 Adaptive Backtest
Weekly rebalance + daily dial monitoring + scenario switching
+ inverse ETF shorts + variable leverage + DBMF

5 scenarios based on stability dial:
  bull_calm    dial < 0.35    90% eq, 1.2x leverage, no shorts
  bull_late    dial 0.35-0.55  80% eq, 1.0x, 5% SH
  stress       dial 0.55-0.75  65% eq, 0.8x, 10% SH + TBF if rates
  crisis       dial > 0.75    40% eq, 0.5x, 15% SH+PSQ, daily rebal
  recovery     dial falling   70% eq, 1.0x, shorts removed

Gate (all 4 required for paper trading):
  Sharpe >= 1.1
  Max drawdown <= 30%
  Calmar >= 0.35
  Final >= $70,000
"""

import os, sys, time, json, warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
CONFIG   = os.path.expanduser("~/tradingbot/config")

# ── Universe ──────────────────────────────────────────────────
RISK_ASSETS = ["VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF"]
DEF_ASSETS  = ["AGG", "TLT", "GLD"]
SHORT_ASSETS = ["SH", "PSQ", "TBF"]
DIVERSIFIER  = ["DBMF"]
ALL_ASSETS   = RISK_ASSETS + DEF_ASSETS + SHORT_ASSETS + DIVERSIFIER

ETF_INCEPTION = {
    "VTI":  "2001-06-15", "QQQ":  "1999-03-10",
    "SCHF": "2009-11-03", "EEM":  "2003-04-11",
    "XLV":  "1998-12-22", "XLF":  "1998-12-22",
    "AGG":  "2003-09-29", "TLT":  "2002-07-26",
    "GLD":  "2004-11-18", "SH":   "2006-06-21",
    "PSQ":  "2006-06-21", "TBF":  "2009-08-20",
    "DBMF": "2019-05-08",
}

# ── Scenario configs ──────────────────────────────────────────
SCENARIOS = {
    "bull_calm": {
        "dial_max":    0.35,
        "equity_target": 0.90,
        "leverage":    1.20,
        "shorts":      {},
        "def_min":     0.05,
        "blend":       "momentum_heavy",
        "dbmf":        0.05,
    },
    "bull_late": {
        "dial_max":    0.55,
        "equity_target": 0.80,
        "leverage":    1.00,
        "shorts":      {"SH": 0.05},
        "def_min":     0.10,
        "blend":       "current",
        "dbmf":        0.06,
    },
    "stress": {
        "dial_max":    0.75,
        "equity_target": 0.65,
        "leverage":    0.80,
        "shorts":      {"SH": 0.08, "TBF": 0.05},
        "def_min":     0.20,
        "blend":       "min_var_heavy",
        "dbmf":        0.08,
    },
    "crisis": {
        "dial_max":    1.00,
        "equity_target": 0.40,
        "leverage":    0.50,
        "shorts":      {"SH": 0.10, "PSQ": 0.05},
        "def_min":     0.35,
        "blend":       "min_var_heavy",
        "dbmf":        0.10,
    },
}

BLENDS = {
    "current": {
        "risk_parity": 0.35, "min_variance": 0.20,
        "max_divers":  0.15, "equal_weight": 0.15,
        "bl_equilibrium": 0.15,
    },
    "momentum_heavy": {
        "risk_parity": 0.15, "min_variance": 0.10,
        "max_divers":  0.10, "equal_weight": 0.10,
        "bl_equilibrium": 0.10, "momentum": 0.45,
    },
    "min_var_heavy": {
        "risk_parity": 0.20, "min_variance": 0.45,
        "max_divers":  0.15, "equal_weight": 0.10,
        "bl_equilibrium": 0.10,
    },
}

TCOST    = 0.0005
LOOKBACK = 504
SVI_STEPS = 1000
SVI_DRAWS = 1000
OPT_DRAWS = 100


def get_scenario(dial, prev_dial=None):
    """Detect current scenario including recovery."""
    # Recovery: dial was high, now falling
    if prev_dial is not None and prev_dial > 0.75 and dial < prev_dial - 0.05:
        return "recovery", {
            "equity_target": 0.70, "leverage": 1.00,
            "shorts": {}, "def_min": 0.15,
            "blend": "risk_parity", "dbmf": 0.07,
        }
    for name, cfg in SCENARIOS.items():
        if dial <= cfg["dial_max"]:
            return name, cfg
    return "crisis", SCENARIOS["crisis"]


def momentum_weights(rets, n=len(RISK_ASSETS)):
    """6-month momentum inverse-vol weighted."""
    lookback = min(126, len(rets))
    if lookback < 20:
        return np.ones(n) / n
    mom  = rets.iloc[-lookback:].mean().values
    vols = rets.std().values
    scores = np.where(vols > 0, mom / vols, 0).clip(min=0)
    if scores.sum() == 0:
        return np.ones(n) / n
    return scores / scores.sum()


def run_adaptive(start="2004-06-30", verbose=True):
    from svi_covariance import fit_svi
    from stability_index import compute_dial, compute_components
    from portfolio_engine import (risk_parity, min_variance,
                                   max_diversification, equal_weight,
                                   bl_equilibrium, _project_simplex_capped)

    # Load prices
    px_path = os.path.join(DATA_DIR, "bt_prices.parquet")
    px = pd.read_parquet(px_path)
    px.index = pd.to_datetime(px.index).tz_localize(None)

    # Load stability dial
    stab = pd.read_parquet(os.path.join(DATA_DIR, "stability.parquet"))
    dial_series = stab["stability_risk"].dropna()

    # Weekly dates
    all_dates = pd.date_range(start=start, end=px.index.max(), freq="W-FRI")
    all_dates = [px.index[px.index <= d].max() for d in all_dates]
    all_dates = [d for d in all_dates if pd.notna(d)]

    port_val   = 10000.0
    weights    = None
    prev_dial  = None
    records    = []
    t0         = time.time()

    print(f"Adaptive backtest: {start} to {px.index.max().date()}")
    print(f"Weekly rebalance | {len(all_dates)} periods | "
          f"SVI {SVI_STEPS}s/{SVI_DRAWS}d")
    print("=" * 70)

    for i, d in enumerate(all_dates):
        # Available assets at this date
        avail = [t for t in RISK_ASSETS + DEF_ASSETS
                 if t in px.columns and
                 pd.Timestamp(ETF_INCEPTION.get(t, "2000-01-01")) <= d]

        # Shorts available
        avail_shorts = [t for t in SHORT_ASSETS
                        if t in px.columns and
                        pd.Timestamp(ETF_INCEPTION.get(t, "2000-01-01")) <= d]

        # DBMF available
        use_dbmf = ("DBMF" in px.columns and
                    pd.Timestamp(ETF_INCEPTION["DBMF"]) <= d)

        if len(avail) < 3:
            continue

        # Price history
        hist = px.loc[:d, avail].dropna(axis=1, thresh=60)
        avail = list(hist.columns)
        if len(avail) < 3:
            continue

        avail_risk = [t for t in RISK_ASSETS if t in avail]
        avail_def  = [t for t in DEF_ASSETS  if t in avail]

        rets = hist.pct_change().dropna().iloc[-LOOKBACK:]
        if len(rets) < 60:
            continue

        # Get dial reading
        dial_val = float(dial_series.asof(d)) if d in dial_series.index \
                   or d > dial_series.index[0] else 0.40

        # Get scenario
        scenario_name, scenario = get_scenario(dial_val, prev_dial)

        # SVI covariance
        try:
            covs, _ = fit_svi(rets, n_steps=SVI_STEPS,
                              n_draws=SVI_DRAWS, verbose=False)
            idx_s = np.linspace(0, len(covs)-1, OPT_DRAWS).astype(int)
            covs_np = covs[idx_s].numpy() * 252
        except Exception:
            continue

        n = len(avail)
        fallback = np.ones(n) / n
        mkt_w    = np.ones(n) / n

        # Model blend for long positions
        blend_name = scenario.get("blend", "current")
        blend = BLENDS.get(blend_name, BLENDS["current"])

        MODEL_FNS = {
            "risk_parity":    risk_parity,
            "min_variance":   min_variance,
            "max_divers":     max_diversification,
            "equal_weight":   equal_weight,
            "bl_equilibrium": None,
            "momentum":       None,
        }

        per_model = {}
        for mname, bwt in blend.items():
            if bwt == 0:
                continue
            try:
                if mname == "bl_equilibrium":
                    w_m = bl_equilibrium(covs_np.mean(0), mkt_w)
                elif mname == "momentum":
                    ri = [avail.index(t) for t in avail_risk if t in avail]
                    if ri:
                        sub_rets = rets.iloc[:, ri]
                        mom_w    = momentum_weights(sub_rets, len(ri))
                        w_m      = np.zeros(n)
                        for ii, ridx in enumerate(ri):
                            w_m[ridx] = mom_w[ii]
                    else:
                        w_m = fallback.copy()
                else:
                    fn = MODEL_FNS[mname]
                    ws = np.stack([fn(c) for c in covs_np])
                    w_m = ws.mean(0)
                if np.isnan(w_m).any() or w_m.sum() == 0:
                    w_m = fallback.copy()
            except Exception:
                w_m = fallback.copy()
            per_model[mname] = w_m

        w = sum(per_model[m] * blend[m]
                for m in blend if m in per_model and blend[m] > 0)
        if np.isnan(w).any() or w.sum() == 0:
            w = fallback.copy()
        else:
            w = _project_simplex_capped(w)

        # Apply equity/defensive split
        eq_target  = scenario["equity_target"]
        def_min    = scenario.get("def_min", 0.10)
        ri = [avail.index(t) for t in avail_risk if t in avail]
        di = [avail.index(t) for t in avail_def  if t in avail]

        if ri and di:
            cr = w[ri].sum()
            if cr > 0:
                w[ri] *= eq_target / cr
                w[di] *= (1 - eq_target) / max(1 - cr, 1e-9)
            w = np.clip(w, 0, None)
            w = w / w.sum()

        # DBMF allocation
        dbmf_w = scenario.get("dbmf", 0.0) if use_dbmf else 0.0
        if dbmf_w > 0 and ri:
            w[ri] *= (1 - dbmf_w)

        w = _project_simplex_capped(w)

        # Build full weight dict including shorts and DBMF
        weight_dict = {avail[j]: float(w[j]) for j in range(n)}

        # Add shorts
        shorts = {k: v for k, v in scenario.get("shorts", {}).items()
                  if k in avail_shorts}
        total_short = sum(shorts.values())
        if total_short > 0 and ri:
            # Reduce long equity to fund shorts
            for t in avail_risk:
                if t in weight_dict:
                    weight_dict[t] *= (1 - total_short)
            for t, sw in shorts.items():
                weight_dict[t] = sw

        # Add DBMF
        if dbmf_w > 0 and use_dbmf:
            weight_dict["DBMF"] = dbmf_w

        # Variable leverage -- scale but cap total at leverage limit
        leverage = scenario.get("leverage", 1.0)
        # For backtesting we apply leverage as return multiplier
        # (simplified -- real margin costs not modeled)

        # Transaction costs
        all_tickers = list(weight_dict.keys())
        if weights is not None:
            old_w = pd.Series(weights).reindex(all_tickers).fillna(0).values
            new_w = np.array([weight_dict.get(t, 0) for t in all_tickers])
            turnover = np.abs(new_w - old_w).sum() / 2
            port_val *= (1 - TCOST * turnover * 2)
        weights = weight_dict

        # Roll forward to next rebalance
        next_d = all_dates[i+1] if i+1 < len(all_dates) else px.index[-1]

        # Compute return
        ret = 0.0
        all_px_tickers = all_tickers + (["DBMF"] if use_dbmf and "DBMF" not in all_tickers else [])
        pp = px.loc[d:next_d, [t for t in weight_dict.keys()
                                if t in px.columns]].dropna(how="all")
        if len(pp) < 2:
            continue
        for t, tw in weight_dict.items():
            if t not in pp.columns:
                continue
            pr = pp[t].dropna()
            if len(pr) < 2:
                continue
            t_ret = float(pr.iloc[-1] / pr.iloc[0] - 1)
            ret += tw * t_ret * leverage

        if np.isnan(ret) or np.isinf(ret):
            continue
        port_val *= (1 + ret)
        if np.isnan(port_val):
            port_val = 10000.0

        prev_dial = dial_val
        records.append({
            "date":     next_d,
            "portfolio": port_val,
            "dial":     dial_val,
            "scenario": scenario_name,
            "leverage": leverage,
        })

        if verbose:
            elapsed = time.time() - t0
            eta = elapsed / (i+1) * (len(all_dates)-i-1) if i > 0 else 0
            pct = (i+1) / len(all_dates) * 100
            bar = "#" * int(pct/2) + "-" * (50-int(pct/2))
            print(f"  [{bar}] {pct:5.1f}%  {d.date()}  "
                  f"${port_val:>9,.0f}  dial={dial_val:.2f}  "
                  f"scen={scenario_name:<10}  ETA={eta/60:.1f}m",
                  flush=True)

    if not records:
        print("No records generated.")
        return None

    series = pd.Series(
        [r["portfolio"] for r in records],
        index=[r["date"] for r in records])

    # Metrics
    years  = (series.index[-1]-series.index[0]).days / 365.25
    total  = series.iloc[-1] / 10000 - 1
    ann    = (1+total)**(1/max(years,1)) - 1
    mrets  = series.pct_change().dropna()
    sharpe = float(mrets.mean()/mrets.std()*np.sqrt(52)) if mrets.std()>0 else 0
    roll_max = series.cummax()
    dd     = (series - roll_max) / roll_max
    max_dd = float(dd.min())
    calmar = ann / max(abs(max_dd), 1e-9)

    print("\n" + "="*70)
    print("ADAPTIVE BACKTEST RESULTS")
    print("="*70)
    print(f"  Final value:    ${series.iloc[-1]:>10,.2f}")
    print(f"  Total return:   {total:>10.1%}")
    print(f"  Ann return:     {ann:>10.1%}")
    print(f"  Sharpe (wkly):  {sharpe:>10.2f}")
    print(f"  Max drawdown:   {max_dd:>10.1%}")
    print(f"  Calmar:         {calmar:>10.2f}")
    print(f"  Years:          {years:>10.1f}")
    print()

    # Gate check
    print("  PAPER TRADING GATE CHECK:")
    gates = {
        "Sharpe >= 1.1":     sharpe >= 1.1,
        "Max DD <= 30%":     max_dd >= -0.30,
        "Calmar >= 0.35":    calmar >= 0.35,
        "Final >= $70,000":  series.iloc[-1] >= 70000,
    }
    all_pass = True
    for name, passed in gates.items():
        icon = "✅" if passed else "❌"
        print(f"    {icon} {name}")
        if not passed:
            all_pass = False
    print()
    print(f"  {'🎉 ALL GATES PASSED — READY FOR PAPER TRADING' if all_pass else '⚠️  GATES NOT MET — REFINE STRATEGY'}")

    # Save results
    results = {
        "final": float(series.iloc[-1]),
        "total": float(total),
        "ann_ret": float(ann),
        "sharpe": float(sharpe),
        "max_dd": float(max_dd),
        "calmar": float(calmar),
        "years": float(years),
        "gates": gates,
        "all_pass": all_pass,
        "records": [{"date": str(r["date"].date()),
                     "portfolio": r["portfolio"],
                     "dial": r["dial"],
                     "scenario": r["scenario"]}
                    for r in records],
    }
    out = os.path.join(DATA_DIR, "adaptive_backtest.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved to {out}")
    print(f"  Runtime: {(time.time()-t0)/60:.0f} minutes")
    return results


if __name__ == "__main__":
    run_adaptive()
