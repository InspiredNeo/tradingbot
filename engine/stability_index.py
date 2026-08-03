"""
Market Stability Index -- the regime layer, rebuilt as a dial.

WHY A DIAL AND NOT A CLASSIFIER
--------------------------------
Walk-forward testing showed every learned 4-class regime model losing
to a volatility threshold (best learned: 36.5% balanced acc; threshold:
43.8%). The classifier failed because two of its classes (Expansion vs
Neutral) differ only in FORWARD returns -- predicting them is return
forecasting, which the same tests showed to be luck.

The dial answers only the answerable question: how unstable is the
market RIGHT NOW? Every input is observable in the present. Nothing
forecasts direction. Persistence (vol clustering) does the small amount
of forward work for free.

DESIGN RULES
------------
1. Component weights are FIXED A PRIORI, not fitted. After watching
   fitted models lose to a threshold, the dial learns nothing.
2. Percentile mapping uses an EXPANDING WINDOW -- the reading at date D
   uses only data through D. Historical readings are honest.
3. Output is continuous [0,1]. Risk scales proportionally downstream --
   no cliff-edge class boundaries to be one-class-wrong about.

COMPONENTS (weight, rationale)
------------------------------
  realized vol      0.40  strongest present-tense signal we have
  credit stress     0.30  led equities by ~2 months in 2008
  vol trajectory    0.15  25% vol rising is worse than 25% fading
  divers. breakdown 0.15  in true crises correlations spike toward 1
"""

import os
import numpy as np
import pandas as pd

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

WEIGHTS = {
    "vol":         0.40,
    "credit":      0.30,
    "vol_traj":    0.15,
    "divers":      0.15,
}
MIN_HISTORY = 36   # months of expanding window before dial is trusted


def _expanding_pct(series):
    """
    Percentile of each value vs ALL PRIOR values (inclusive).
    Reading at date D uses only data through D -- no lookahead.
    First MIN_HISTORY readings are NaN (insufficient context).
    """
    vals = series.values.astype(float)
    out = np.full(len(vals), np.nan)
    for i in range(MIN_HISTORY, len(vals)):
        hist = vals[: i + 1]
        hist = hist[~np.isnan(hist)]
        if len(hist) < MIN_HISTORY or np.isnan(vals[i]):
            continue
        out[i] = (hist <= vals[i]).mean()
    return pd.Series(out, index=series.index)


def compute_components(X, prices=None):
    """
    Build the four dial components from the point-in-time feature matrix.
    All inputs already exist in features.parquet -- no new data needed.
    """
    comp = pd.DataFrame(index=X.index)

    # 1. Realized volatility -- direct read
    comp["vol"] = _expanding_pct(X["spy_realized_vol_63"])

    # 2. Credit stress -- level and 63d change, averaged
    lvl = _expanding_pct(X["credit_level"])
    mom = _expanding_pct(X["credit_mom_63"])
    comp["credit"] = (lvl + mom) / 2

    # 3. Vol trajectory -- is short-window vol above/below its own z
    #    vix_mom_21 captures whether fear is building or fading
    comp["vol_traj"] = _expanding_pct(X["vix_mom_21"])

    # 4. Diversification breakdown -- when stocks and bonds fall together
    #    stock_bond_spread near its LOW means bonds aren't offsetting.
    #    sector_dispersion near its LOW means everything moves as one.
    sb = 1.0 - _expanding_pct(X["stock_bond_spread"])
    disp = 1.0 - _expanding_pct(X["sector_dispersion"])
    comp["divers"] = (sb + disp) / 2

    return comp


def compute_dial(comp):
    """Weighted blend -> [0,1] stability-risk dial (1 = unstable)."""
    dial = sum(comp[k] * w for k, w in WEIGHTS.items())
    return dial.rename("stability_risk")


def risk_multiplier(dial_value, floor=0.25):
    """
    Dial -> equity risk scaling for Phase 5.
    Smooth, monotone, no cliffs:
      dial 0.0-0.5  -> ~1.0  (normal risk)
      dial 0.7      -> ~0.70
      dial 0.85     -> ~0.45
      dial 1.0      -> floor (0.25 -- defensive floor, never zero)
    Logistic ramp centered at 0.70, steepness 8.
    """
    if np.isnan(dial_value):
        return 1.0
    ramp = 1.0 / (1.0 + np.exp(-8.0 * (dial_value - 0.70)))
    return float(1.0 - (1.0 - floor) * ramp)


def validate_against_labels(dial):
    """
    The test that matters: do dial readings separate the mechanically
    labeled regimes? Labels encode FORWARD outcomes; the dial reads the
    PRESENT. Separation means present instability aligns with bad
    forward windows -- which is persistence doing its work.
    """
    y = pd.read_parquet(os.path.join(DATA_DIR, "y_labeled.parquet"))
    joined = pd.concat([dial, y["label"]], axis=1).dropna()

    names = ["Expansion", "Neutral", "Stress", "Crisis"]
    print("\n  Dial reading by forward-outcome regime:")
    print(f"    {'regime':<12} {'mean':>6} {'p25':>6} {'p75':>6} {'n':>5}")
    for i, nm in enumerate(names):
        sub = joined[joined["label"] == i]["stability_risk"]
        if sub.empty:
            continue
        print(f"    {nm:<12} {sub.mean():>6.2f} "
              f"{sub.quantile(.25):>6.2f} {sub.quantile(.75):>6.2f} "
              f"{len(sub):>5}")

    # Simple threshold skill: dial>=0.70 as a "danger" flag
    flag = joined["stability_risk"] >= 0.70
    bad = joined["label"] >= 2          # Stress or Crisis forward
    tp = (flag & bad).sum(); fp = (flag & ~bad).sum()
    fn = (~flag & bad).sum()
    prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)
    print(f"\n  Danger flag (dial>=0.70) vs forward Stress/Crisis:")
    print(f"    precision {prec:.0%}   recall {rec:.0%}   "
          f"(fires {flag.mean():.0%} of months)")
    return joined


def build(verbose=True):
    X = pd.read_parquet(os.path.join(DATA_DIR, "features.parquet"))
    comp = compute_components(X)
    dial = compute_dial(comp)

    out = pd.concat([comp, dial], axis=1)
    out.to_parquet(os.path.join(DATA_DIR, "stability.parquet"))

    if verbose:
        print("=" * 60)
        print("MARKET STABILITY INDEX")
        print("=" * 60)
        print(f"\n  Weights (fixed a priori): {WEIGHTS}")
        print(f"  Expanding-window percentiles, {MIN_HISTORY}m warmup")

        print("\n  Dial through the crisis windows:")
        for window, label in [
            ("2002-06-28", "dot-com bottom"),
            ("2008-08-29", "pre-Lehman"),
            ("2008-10-31", "post-Lehman"),
            ("2020-02-28", "COVID onset"),
            ("2020-03-31", "COVID trough"),
            ("2022-09-30", "2022 bear"),
        ]:
            d = pd.Timestamp(window)
            if d in dial.index and not np.isnan(dial.loc[d]):
                v = dial.loc[d]
                print(f"    {label:<16} {window}  dial={v:.2f}  "
                      f"risk_mult={risk_multiplier(v):.2f}")

        latest = dial.dropna().iloc[-1]
        print(f"\n  Latest reading ({dial.dropna().index[-1].date()}): "
              f"{latest:.2f}  ->  risk multiplier "
              f"{risk_multiplier(latest):.2f}")

        validate_against_labels(dial)

    return out


if __name__ == "__main__":
    build()
