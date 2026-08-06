"""
Fast allocation sanity check -- no SVI, no optimization.
Runs the full 2004-2026 weekly loop in ~20 seconds.

Verifies the allocation LOGIC only:
  - does equity track the dial sensibly?
  - does it ever latch or stop responding?
  - how much time in each regime?
  - rough return path (equal-weight proxy, not real portfolio)

If this looks wrong, the real backtest will be wrong.
If this looks right, it is worth spending 8 hours on SVI.
"""
import os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from adaptive_backtest_v2 import (
    compute_market_implied_dial, continuous_allocation,
    get_scenario_label, THRESHOLDS,
)

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

DERISK_MAX = 0.15   # max weekly move toward defense
RERISK_MAX = 0.06   # max weekly move toward risk

RISK  = ["VTI","QQQ","SCHF","EEM","XLV","XLF"]
DEF   = ["AGG","TLT","GLD"]
SHORT = ["SH","PSQ","TBF"]


def run(verbose=False):
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    dates = pd.date_range("2004-06-30", px.index.max(), freq="W-FRI")
    dates = [px.index[px.index <= d].max() for d in dates]
    dates = [d for d in dates if pd.notna(d)]

    equity_now = 0.70
    val = 10000.0
    rows = []

    for i, d in enumerate(dates[:-1]):
        try:
            dial = compute_market_implied_dial(px, d)
        except Exception:
            continue

        alloc = continuous_allocation(dial)
        target = alloc["equity_target"]

        # Rate-limited move -- the entire control logic
        if target < equity_now:
            step = max(target - equity_now, -DERISK_MAX)
        else:
            step = min(target - equity_now, RERISK_MAX)
        equity_now += step

        # Equal-weight proxy return
        nxt = dates[i+1]
        avail_r = [t for t in RISK if t in px.columns
                   and not pd.isna(px.loc[d, t])]
        avail_d = [t for t in DEF if t in px.columns
                   and not pd.isna(px.loc[d, t])]
        if not avail_r or not avail_d:
            continue

        def sleeve_ret(tickers):
            rs = []
            for t in tickers:
                try:
                    a = float(px.loc[d, t]); b = float(px.loc[nxt, t])
                    if a > 0: rs.append(b/a - 1)
                except Exception:
                    pass
            return float(np.mean(rs)) if rs else 0.0

        shorts_w = sum(alloc["shorts"].values())
        avail_s = [t for t in SHORT if t in px.columns
                   and not pd.isna(px.loc[d, t])]
        s_ret = sleeve_ret(avail_s) if (avail_s and shorts_w > 0) else 0.0

        r = (equity_now * sleeve_ret(avail_r)
             + (1 - equity_now - shorts_w) * sleeve_ret(avail_d)
             + shorts_w * s_ret)

        if np.isfinite(r):
            val *= (1 + r)

        rows.append({"date": nxt, "dial": dial, "equity": equity_now,
                     "label": get_scenario_label(dial), "val": val,
                     "shorts": shorts_w})

        if verbose and i % 100 == 0:
            print(f"  {d.date()}  dial={dial:.3f}  "
                  f"eq={equity_now:.1%}  ${val:,.0f}")

    return pd.DataFrame(rows).set_index("date")


def report(df):
    print("=" * 66)
    print("DRY RUN -- ALLOCATION LOGIC CHECK")
    print("=" * 66)

    print(f"\nPeriods: {len(df)}")
    print(f"Proxy final: ${df['val'].iloc[-1]:,.0f} "
          f"(equal-weight, NOT the real backtest)")

    print(f"\nEQUITY ALLOCATION:")
    print(f"  min {df['equity'].min():.1%}  "
          f"max {df['equity'].max():.1%}  "
          f"mean {df['equity'].mean():.1%}")

    print(f"\nDIAL:")
    print(f"  min {df['dial'].min():.3f}  "
          f"max {df['dial'].max():.3f}  "
          f"mean {df['dial'].mean():.3f}")

    print(f"\nTIME IN EACH REGIME (by dial):")
    for lbl in ["bull_calm","bull_late","stress","crisis"]:
        n = (df["label"] == lbl).sum()
        print(f"  {lbl:<12} {n:>5} weeks  {n/len(df):>6.1%}")

    # Latch detection -- the failure mode that cost us tonight
    print(f"\nLATCH CHECK:")
    eq = df["equity"].round(4)
    runs, cur, mx, mx_at = 1, eq.iloc[0], 1, df.index[0]
    for j in range(1, len(eq)):
        if eq.iloc[j] == cur:
            runs += 1
            if runs > mx:
                mx, mx_at = runs, df.index[j]
        else:
            runs, cur = 1, eq.iloc[j]
    print(f"  Longest unchanged equity run: {mx} weeks (ending {mx_at.date()})")
    print(f"  {'FAIL -- possible latch' if mx > 12 else 'OK -- responsive'}")

    # Does equity actually track the dial?
    corr = df["equity"].corr(df["dial"])
    print(f"\n  Equity/dial correlation: {corr:+.3f}")
    print(f"  {'OK -- inverse as expected' if corr < -0.5 else 'FAIL -- not tracking'}")

    print(f"\nKEY DATES:")
    for ds in ["2008-09-30","2008-11-28","2009-03-31","2012-06-30",
               "2017-12-31","2018-10-31","2020-03-31","2022-06-30",
               "2024-12-31"]:
        t = pd.Timestamp(ds)
        sub = df[df.index <= t]
        if len(sub):
            r = sub.iloc[-1]
            print(f"  {ds}  dial={r['dial']:.3f}  "
                  f"eq={r['equity']:>5.1%}  "
                  f"short={r['shorts']:>4.1%}  {r['label']}")

    print(f"\nDRAWDOWN (proxy): "
          f"{((df['val']/df['val'].cummax())-1).min():.1%}")
    print("=" * 66)


if __name__ == "__main__":
    import time
    t0 = time.time()
    df = run(verbose=True)
    print(f"\n[{time.time()-t0:.1f}s]\n")
    report(df)
    df.to_parquet(os.path.join(DATA_DIR, "dryrun_v2.parquet"))
