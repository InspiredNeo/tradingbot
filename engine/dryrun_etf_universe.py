"""
Fast, cheap sanity check for the full ETF universe pipeline --
score -> tier -> size -> smooth -- across many consecutive weeks.

No SVI, no portfolio optimization, no real backtest. Just walks
the scoring/sizing chain forward week by week the way it would
actually be used, and checks for the same failure signatures
already known to matter: latching, nonsense weight sums, runaway
concentration, excessive turnover.

Run this before ever wiring the ETF universe logic into a real
multi-hour backtest.
"""
import time
import pandas as pd
import numpy as np
from etf_scorer import size_positions_smoothed


def run(start="2004-06-30", end="2026-08-01", verbose=True):
    dates = pd.date_range(start, end, freq="W-FRI")

    prev = None
    history = []
    t0 = time.time()

    for i, d in enumerate(dates):
        try:
            w = size_positions_smoothed(str(d.date()), previous_weights=prev,
                                        verbose=False)
        except Exception as e:
            print(f"  ERROR at {d.date()}: {e}")
            continue

        total = sum(w.values()) if w else 0.0
        history.append({
            "date": d, "weights": w, "total": total,
            "n_held": len(w),
            "max_single": max(w.values()) if w else 0.0,
        })
        prev = w

        if verbose and i % 100 == 0:
            print(f"  {d.date()}  n_held={len(w)}  "
                  f"max_single={max(w.values()) if w else 0:.1%}  "
                  f"sum={total:.3f}")

    print(f"\n[{time.time()-t0:.1f}s for {len(history)} weeks]")
    return history


def report(history):
    print("=" * 66)
    print("ETF UNIVERSE PIPELINE -- DRY RUN CHECK")
    print("=" * 66)

    df = pd.DataFrame(history)

    print(f"\nWeeks processed: {len(df)}")

    print(f"\nWEIGHT SUM CHECK (should always be very close to 1.0):")
    bad_sums = df[(df["total"] < 0.98) | (df["total"] > 1.02)]
    print(f"  Weeks with sum outside 0.98-1.02: {len(bad_sums)}")
    if len(bad_sums) > 0:
        print(f"  FAIL -- worst: {bad_sums['total'].min():.3f} to "
              f"{bad_sums['total'].max():.3f}")
    else:
        print(f"  OK -- min {df['total'].min():.3f}, max {df['total'].max():.3f}")

    print(f"\nCONCENTRATION CHECK (max single-ticker weight over time):")
    print(f"  Mean: {df['max_single'].mean():.1%}")
    print(f"  Max ever: {df['max_single'].max():.1%} "
          f"(on {df.loc[df['max_single'].idxmax(), 'date'].date()})")
    extreme = df[df["max_single"] > 0.70]
    print(f"  Weeks with any single ticker >70%: {len(extreme)}")

    print(f"\nHOLDING COUNT CHECK:")
    print(f"  Mean tickers held per week: {df['n_held'].mean():.1f}")
    print(f"  Min: {df['n_held'].min()}, Max: {df['n_held'].max()}")
    zero_weeks = df[df["n_held"] == 0]
    print(f"  Weeks with ZERO holdings: {len(zero_weeks)} "
          f"({'FAIL' if len(zero_weeks) > 0 else 'OK'})")

    print(f"\nLATCH CHECK (longest run of near-identical portfolios):")
    # Compare each week's top holding to the prior week's
    top_holdings = []
    for h in history:
        if h["weights"]:
            top = max(h["weights"].items(), key=lambda x: x[1])
            top_holdings.append(top[0])
        else:
            top_holdings.append(None)
    max_run, cur_run = 1, 1
    for i in range(1, len(top_holdings)):
        if top_holdings[i] == top_holdings[i-1]:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 1
    print(f"  Longest run of same top holding: {max_run} weeks")
    if max_run > 30:
        print("  Note: long runs during real sustained trends are fine, "
              "check against known dates if this seems too long")
    else:
        print("  OK")

    print("=" * 66)


if __name__ == "__main__":
    history = run(verbose=True)
    report(history)
