"""
Fast, lightweight backtest of the NEW regime-based allocation
system (breadth + correlation detector) -- no SVI, no full
portfolio optimization, just equity vs defensive split using the
proven simple-proxy approach from earlier dry runs this session.

This is the real test of the core hypothesis: does a genuinely
aggressive CALM regime, detected via breadth+correlation instead
of a scalar dial, actually close the calm-year drag gap found
earlier tonight -- or not.
"""
import pandas as pd
import numpy as np
import json
import os
import time

from regime_allocation import get_regime_allocation

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

RISK = ["VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF"]
DEF = ["AGG", "TLT", "GLD"]


def run(start="2004-06-30", end=None, verbose=True):
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    end_date = pd.Timestamp(end) if end else px.index.max()
    dates = pd.date_range(start, end_date, freq="W-FRI")
    dates = [px.index[px.index <= d].max() for d in dates]
    dates = [d for d in dates if pd.notna(d)]

    val = 10000.0
    equity_now = 0.70
    rows = []
    t0 = time.time()

    for i, d in enumerate(dates[:-1]):
        try:
            alloc = get_regime_allocation(px, d, universe, current_equity=equity_now)
        except Exception as e:
            if verbose and i % 100 == 0:
                print(f"  {d.date()}: regime calc failed ({e}), holding steady")
            rows.append({"date": d, "val": val, "equity": equity_now, "regime": "ERROR"})
            continue

        equity_now = alloc["equity_target"]
        regime = alloc["regime"]

        nxt = dates[i + 1]
        avail_r = [t for t in RISK if t in px.columns and not pd.isna(px.loc[d, t])]
        avail_d = [t for t in DEF if t in px.columns and not pd.isna(px.loc[d, t])]
        if not avail_r or not avail_d:
            continue

        def sleeve_ret(tickers):
            rs = []
            for t in tickers:
                try:
                    a, b = float(px.loc[d, t]), float(px.loc[nxt, t])
                    if a > 0:
                        rs.append(b / a - 1)
                except Exception:
                    pass
            return float(np.mean(rs)) if rs else 0.0

        r = equity_now * sleeve_ret(avail_r) + (1 - equity_now) * sleeve_ret(avail_d)
        if np.isfinite(r):
            val *= (1 + r)

        rows.append({"date": nxt, "val": val, "equity": equity_now, "regime": regime})

        if verbose and i % 50 == 0:
            print(f"  {d.date()}  regime={regime:<20} eq={equity_now:.1%}  ${val:,.0f}")

    elapsed = time.time() - t0
    print(f"\n[{elapsed:.1f}s for {len(rows)} periods]")

    df = pd.DataFrame(rows)
    print(f"\nFinal value: ${df['val'].iloc[-1]:,.0f}")
    print(f"\nRegime distribution:")
    print(df["regime"].value_counts())

    return df


if __name__ == "__main__":
    run(start="2004-06-30", verbose=True)
