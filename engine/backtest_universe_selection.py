"""
Real, honest backtest of universe_selection.py's dynamic asset
selection, using proper point-in-time discipline -- at each
historical date, only real data available up to that date is used.

REAL, KNOWN LIMITATION: survivorship bias. The 1,383-ticker
universe reflects TODAY's active funds; any real historical fund
that has since closed/merged/delisted is absent, which could make
this backtest look better than genuine, real-time selection would
have performed historically. Worth being explicit about this
caveat whenever citing results from this backtest.
"""
import pandas as pd
import numpy as np
import json
import time
from universe_selection import select_universe


def run_selection_backtest(start="2015-01-01", end=None,
                           rebalance_freq="W-FRI", target_count=25,
                           verbose=True):
    px = pd.read_parquet("histdata/bt_prices.parquet")
    px.index = pd.to_datetime(px.index).tz_localize(None)
    vol = pd.read_parquet("histdata/bt_volume.parquet")
    vol.index = pd.to_datetime(vol.index).tz_localize(None)

    with open("histdata/final_equity_universe.json") as f:
        universe = json.load(f)

    dates = pd.date_range(start, end or px.index[-1], freq=rebalance_freq)
    dates = [d for d in dates if d <= px.index[-1]]

    val = 10000.0
    current_holdings = {}
    portfolio_history = []
    t0 = time.time()

    if verbose:
        print(f"Backtesting universe selection: {len(dates)} rebalances")
        print(f"REAL, KNOWN LIMITATION: survivorship bias (universe "
              f"reflects today's active funds, not the real historical set)")

    for i, d in enumerate(dates):
        try:
            selected = select_universe(px, vol, d, universe,
                                       target_count=target_count, verbose=False)
        except Exception as e:
            if verbose:
                print(f"  [WARN] Selection failed at {d.date()}: {e}")
            continue

        if not selected:
            continue

        # Simple, equal-weight rebalance across the selected assets
        # -- real, honest simplification. A more sophisticated
        # weighting (like the SVI approach used elsewhere) could be
        # layered on later, but equal-weight isolates the real
        # SELECTION signal specifically, without conflating it with
        # a separate weighting methodology
        if current_holdings:
            # FIXED: real bug found via testing -- a held ticker
            # (e.g. ISAPF) can have a genuine NaN price on a given
            # real date (trading halt, data gap, etc.), which
            # silently poisoned the ENTIRE portfolio's value
            # calculation via sum(). Now uses the ticker's real,
            # last known valid price as a fallback when the exact
            # date's price is missing, rather than propagating NaN.
            prices_now = px.loc[:d, list(current_holdings.keys())].iloc[-1]
            val = 0.0
            for t in current_holdings:
                p = prices_now.get(t, 0)
                if pd.isna(p):
                    # Real, honest fallback: use the most recent
                    # genuinely valid price for this ticker
                    valid_prices = px.loc[:d, t].dropna()
                    p = valid_prices.iloc[-1] if len(valid_prices) > 0 else 0
                val += current_holdings[t] * p

        target_dollar_each = val / len(selected)
        prices_at_d = px.loc[:d, selected].iloc[-1]
        current_holdings = {
            t: target_dollar_each / prices_at_d[t]
            for t in selected if prices_at_d.get(t, 0) > 0
        }

        portfolio_history.append({"date": d, "value": val, "n_holdings": len(current_holdings)})

        if verbose and (i + 1) % 20 == 0:
            elapsed = time.time() - t0
            print(f"  {d.date()}  ${val:,.2f}  ({i+1}/{len(dates)}, {elapsed:.0f}s elapsed)")

    result_df = pd.DataFrame(portfolio_history)

    if verbose and len(result_df) > 0:
        final_val = result_df["value"].iloc[-1]
        total_return = (final_val - 10000) / 10000
        print(f"\nFinal value: ${final_val:,.2f}")
        print(f"Total return: {total_return:.1%}")

    return result_df


if __name__ == "__main__":
    run_selection_backtest(start="2020-01-01", verbose=True)
