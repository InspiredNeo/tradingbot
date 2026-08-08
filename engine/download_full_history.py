"""
Downloads full historical price data for the validated 1,368-
ticker equity universe, in small, paced batches to respect
yfinance rate limits (already hit once this session). Merges into
the existing bt_prices.parquet cache. Checkpointed and safely
re-runnable.
"""
import pandas as pd
import yfinance as yf
import json
import os
import time

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
PROGRESS_FILE = os.path.join(DATA_DIR, "history_download_progress.json")


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"downloaded": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def run(batch_size=50, max_batches=3, pause_seconds=5, verbose=True):
    """
    Small batches (50, not 150) and a pause between each, since
    we're now downloading full multi-year history per ticker
    (heavier request) rather than the lighter recent-window check
    used for the liquidity validation earlier.
    """
    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        full_universe = json.load(f)

    progress = load_progress()
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    already_have = set(px.columns) | set(progress["downloaded"])

    remaining = [t for t in full_universe if t not in already_have]

    if verbose:
        print(f"Full universe: {len(full_universe)}")
        print(f"Already cached: {len(already_have)}")
        print(f"Remaining to download: {len(remaining)}")
        print()

    for batch_num in range(max_batches):
        if not remaining:
            print("All tickers downloaded.")
            break

        batch = remaining[:batch_size]
        remaining = remaining[batch_size:]

        if verbose:
            print(f"Batch {batch_num+1}/{max_batches}: downloading {len(batch)} tickers...")

        try:
            new_data = yf.download(batch, start="2000-01-01",
                                   progress=False, auto_adjust=True, threads=True)
            close_data = new_data["Close"] if len(batch) > 1 else new_data[["Close"]]
            close_data.index = pd.to_datetime(close_data.index).tz_localize(None)

            succeeded = [t for t in batch if t in close_data.columns
                        and not close_data[t].dropna().empty]

            px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
            px = px.join(close_data[succeeded], how="outer").sort_index()
            px.to_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))

            progress["downloaded"].extend(succeeded)
            save_progress(progress)

            if verbose:
                print(f"  Succeeded: {len(succeeded)}/{len(batch)}")
                print(f"  Total cached now: {len(progress['downloaded']) + len(already_have) - len(progress['downloaded'])}")
                print()

        except Exception as e:
            print(f"  Batch failed: {e}")
            print("  Stopping here -- possible rate limit, resume later.")
            break

        if batch_num < max_batches - 1:
            time.sleep(pause_seconds)

    return progress


if __name__ == "__main__":
    run(batch_size=50, max_batches=3, pause_seconds=5)
