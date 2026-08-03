"""
Mechanical regime labeling from forward-looking market outcomes.

DESIGN DECISIONS AND WHY
------------------------
1. FOUR regimes, not eight. With 254 monthly samples, 8 classes leaves
   ~30 per class and crisis would have <12. The Bull-Strong vs
   Bull-Late-Cycle split had no mechanical definition -- it required my
   judgement, which reintroduces the synthetic-data mirror problem.
   Collapsed to regimes that a rule can actually separate.

2. HYBRID window: D-21d to D+63d. Pure forward labeling asks the model
   to forecast returns (very hard, expect ~35% accuracy). Pure
   contemporaneous labeling is trivially learnable from the vol feature
   and adds nothing over a threshold. The hybrid captures regime state.

3. LABELS ENCODE THE FUTURE. The label for date D uses data through
   D+63 trading days. Any validation split must leave a >63-day gap
   between train and test or the leakage is severe. embargo_days
   handles this and is NOT optional.

4. Last ~3 months are unlabelable -- forward window hasn't elapsed.
   Those rows are dropped, not filled.
"""

import os
import json
import numpy as np
import pandas as pd

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

REGIME_NAMES = ["Expansion", "Neutral", "Stress", "Crisis"]
FORWARD_DAYS = 63    # ~3 months
BACKWARD_DAYS = 21   # ~1 month
EMBARGO_DAYS = FORWARD_DAYS + 5   # validation gap; label lookahead + buffer


def load_spy_history():
    prices = pd.read_parquet(os.path.join(DATA_DIR, "prices.parquet"))
    return prices["spy"].dropna()


def compute_outcomes(spy, dates):
    """
    For each sample date, compute the outcome statistics that define
    its regime. Window spans D-21d to D+63d.
    """
    rows = []
    idx = spy.index

    for d in dates:
        pos = idx.searchsorted(d)
        if pos >= len(idx):
            continue
        fwd_end = pos + FORWARD_DAYS
        if fwd_end >= len(idx):
            rows.append({"date": d, "labelable": False})
            continue

        back_start = max(0, pos - BACKWARD_DAYS)
        window = spy.iloc[back_start:fwd_end + 1]
        fwd = spy.iloc[pos:fwd_end + 1]

        fwd_ret = float(fwd.iloc[-1] / fwd.iloc[0] - 1)
        rets = window.pct_change().dropna()
        realized_vol = float(rets.std() * np.sqrt(252))
        peak = float(window.cummax().iloc[-1])
        trough_after_peak = float(fwd.min())
        max_dd = float(trough_after_peak / peak - 1)
        worst_day = float(rets.min())

        rows.append({
            "date": d, "labelable": True,
            "fwd_return": fwd_ret,
            "realized_vol": realized_vol,
            "max_drawdown": max_dd,
            "worst_day": worst_day,
        })

    return pd.DataFrame(rows).set_index("date")


def assign_labels(outcomes, vol_crisis=0.33, dd_crisis=-0.20,
                  vol_stress=0.225, dd_stress=-0.155,
                  ret_expansion=0.041, vol_expansion=0.133):
    """
    Rule-based regime assignment, calibrated to the EMPIRICAL
    distribution of outcomes rather than to priors.

    First calibration produced 61% Stress -- a degenerate majority class
    where predicting one label always scores 61% accuracy. Cause: the
    original vol_stress=0.20 sat at the 79th percentile while
    dd_stress=-0.08 was LOOSER than the median drawdown (-0.096), so the
    OR condition swept in nearly everything.

    Thresholds now anchored to observed quantiles:
      vol:  p50=0.133  p75=0.187  p85=0.225  p95=0.334
      dd:   p50=-0.096 p25=-0.125 p10=-0.167
      ret:  p50=0.041  p75=0.077

    Crisis:    vol >= p95 AND dd <= ~p5. Both required -- a vol spike
               without price damage is not a crisis.
    Stress:    vol >= p85 OR dd <= ~p12. Genuine tail, not the middle.
    Expansion: forward return above median AND vol below median.
    Neutral:   everything else -- the broad middle, and the largest
               class by construction, which is honest.
    """
    labels = []
    for d, r in outcomes.iterrows():
        if not r.get("labelable", False):
            labels.append(np.nan)
            continue
        vol = r["realized_vol"]
        dd = r["max_drawdown"]
        ret = r["fwd_return"]

        if vol >= vol_crisis and dd <= dd_crisis:
            labels.append(3)          # Crisis
        elif vol >= vol_stress or dd <= dd_stress:
            labels.append(2)          # Stress
        elif ret >= ret_expansion and vol < vol_expansion:
            labels.append(0)          # Expansion
        else:
            labels.append(1)          # Neutral

    out = outcomes.copy()
    out["label"] = labels
    return out


def build_labels(verbose=True):
    feat_path = os.path.join(DATA_DIR, "features.parquet")
    X = pd.read_parquet(feat_path)
    spy = load_spy_history()

    outcomes = compute_outcomes(spy, X.index)
    labeled = assign_labels(outcomes)

    valid = labeled["label"].notna()
    n_dropped = (~valid).sum()
    labeled = labeled[valid].copy()
    labeled["label"] = labeled["label"].astype(int)

    X = X.loc[labeled.index]

    if verbose:
        print("=" * 64)
        print("REGIME LABELING")
        print("=" * 64)
        print(f"\n  Window: D-{BACKWARD_DAYS}d to D+{FORWARD_DAYS}d")
        print(f"  Samples: {len(labeled)} "
              f"({n_dropped} dropped -- forward window incomplete)")
        print(f"  Required validation embargo: {EMBARGO_DAYS} days\n")

        counts = labeled["label"].value_counts().sort_index()
        print("  Class distribution:")
        for i, name in enumerate(REGIME_NAMES):
            n = int(counts.get(i, 0))
            pct = n / len(labeled) * 100
            bar = "#" * int(pct / 2)
            print(f"    {i} {name:<11} {n:>4} ({pct:5.1f}%) {bar}")

        print("\n  Outcome stats by regime:")
        print(f"    {'regime':<12} {'fwd_ret':>9} {'vol':>8} "
              f"{'max_dd':>9} {'worst_day':>10}")
        for i, name in enumerate(REGIME_NAMES):
            sub = labeled[labeled["label"] == i]
            if sub.empty:
                continue
            print(f"    {name:<12} {sub['fwd_return'].mean():>8.1%} "
                  f"{sub['realized_vol'].mean():>7.1%} "
                  f"{sub['max_drawdown'].mean():>8.1%} "
                  f"{sub['worst_day'].mean():>9.1%}")

        print("\n  Crisis periods identified:")
        crisis = labeled[labeled["label"] == 3]
        if crisis.empty:
            print("    NONE -- thresholds are too strict, review them")
        else:
            for d, r in crisis.iterrows():
                print(f"    {d.date()}  vol={r['realized_vol']:.1%}  "
                      f"dd={r['max_drawdown']:.1%}")

        # Autocorrelation -- the number that determines effective sample size
        lab = labeled["label"].values
        same = (lab[1:] == lab[:-1]).mean()
        print(f"\n  Adjacent-month label agreement: {same:.1%}")
        print(f"  -> ~{len(labeled) * (1 - same):.0f} effective "
              f"independent transitions out of {len(labeled)} samples")

    X.to_parquet(os.path.join(DATA_DIR, "X_labeled.parquet"))
    labeled.to_parquet(os.path.join(DATA_DIR, "y_labeled.parquet"))

    meta = {
        "n_samples": int(len(labeled)),
        "n_features": int(X.shape[1]),
        "regime_names": REGIME_NAMES,
        "forward_days": FORWARD_DAYS,
        "backward_days": BACKWARD_DAYS,
        "embargo_days": EMBARGO_DAYS,
        "class_counts": {REGIME_NAMES[i]: int((labeled["label"] == i).sum())
                         for i in range(4)},
        "warning": (
            "Labels encode data through D+63 trading days. Validation "
            "splits MUST embargo at least EMBARGO_DAYS between train and "
            "test or results are leakage-inflated."),
    }
    with open(os.path.join(DATA_DIR, "labels_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    return X, labeled


if __name__ == "__main__":
    X, y = build_labels()
    print(f"\n  Saved: X={X.shape}, y={len(y)}")
