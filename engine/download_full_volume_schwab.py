"""
Downloads real, full 2-year daily volume data for the complete
1,383-ticker universe using Schwab's API (not yfinance) -- per
real, direct correction: Schwab has no meaningful rate limit,
unlike yfinance's free tier which has repeatedly caused real
problems tonight. Extracts volume alongside price from the same
real candle data Schwab already returns.
"""
import pandas as pd
import json
import time
from datetime import datetime
from schwab_client import get_schwab_client


def download_volume(verbose=True):
    with open("histdata/final_equity_universe.json") as f:
        universe = json.load(f)

    client = get_schwab_client()
    if not client.connected:
        print("Not connected to Schwab")
        return None

    all_volume = {}
    failed = []

    for i, symbol in enumerate(universe):
        try:
            resp = client.client.get_price_history_every_day(symbol)
            data = resp.json()
            candles = data.get("candles", [])

            if not candles:
                failed.append(symbol)
                continue

            dates = [datetime.fromtimestamp(c["datetime"] / 1000).date()
                    for c in candles]
            volumes = [c["volume"] for c in candles]
            series = pd.Series(volumes, index=pd.to_datetime(dates), name=symbol)
            # Keep only the most recent ~2 years, matching the
            # price data's real, existing scope
            all_volume[symbol] = series.iloc[-504:]

        except Exception as e:
            failed.append(symbol)

        if verbose and (i + 1) % 50 == 0:
            pct = (i + 1) / len(universe) * 100
            print(f"  {pct:.1f}%  {i+1}/{len(universe)}  "
                  f"succeeded={len(all_volume)}  failed={len(failed)}")

    vol_df = pd.DataFrame(all_volume)
    vol_df.to_parquet("histdata/bt_volume.parquet")

    if verbose:
        print(f"\nSaved: {len(vol_df.columns)} tickers with real volume data")
        if failed:
            print(f"Failed ({len(failed)}): {failed[:20]}"
                  f"{'...' if len(failed) > 20 else ''}")

    return vol_df


if __name__ == "__main__":
    download_volume(verbose=True)
