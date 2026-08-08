"""
Systematic, batch-by-batch construction of the full ETF universe
from Schwab's real instrument search, filtered mechanically for
liquidity and appropriateness. Processes in batches to manage
download load and allow checkpointing -- can be re-run to
continue where it left off.
"""
import pandas as pd
import numpy as np
import yfinance as yf
import os
import json
import time

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
PROGRESS_FILE = os.path.join(DATA_DIR, "universe_build_progress.json")

EXCLUDE_KEYWORDS = [
    '2X', '3X', 'INVERSE', 'BULL', 'BEAR', 'DAILY TARGET',
    'LEVERAGED', 'ULTRA', 'SHORT ', ' SHORT', 'FLOOR', 'BUFFER',
]

MIN_HISTORY = 504
MIN_DOLLAR_VOL = 1e6


def get_all_appropriate_candidates():
    """Pull the full candidate list from Schwab, apply the
    category/format filters already validated -- returns the
    full ~4,494-ticker appropriate list, unfiltered by liquidity."""
    from schwab_client import get_schwab_client

    client = get_schwab_client()
    results = client.search_instruments_by_description(
        '.*ETF.*', max_results=None)
    etf_only = [r for r in results if r['asset_type'] == 'ETF']
    clean = [r for r in etf_only if not r['symbol'].startswith('$')
             and '.' not in r['symbol'] and 1 <= len(r['symbol']) <= 5]

    def is_appropriate(desc):
        d = desc.upper()
        return not any(kw in d for kw in EXCLUDE_KEYWORDS)

    appropriate = [r for r in clean if is_appropriate(r['description'])]
    return appropriate


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"processed_symbols": [], "validated_survivors": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def process_batch(batch_symbols, verbose=True):
    """Download, check history + real liquidity for one batch.
    Returns list of symbols that survive both checks."""
    if not batch_symbols:
        return []

    try:
        data = yf.download(batch_symbols, start="2015-01-01",
                           progress=False, auto_adjust=True, threads=True)
    except Exception as e:
        if verbose:
            print(f"  Batch download failed entirely: {e}")
        return []

    if len(batch_symbols) == 1:
        close_data = data[["Close"]]
        vol_data = data[["Volume"]]
    else:
        close_data = data["Close"]
        vol_data = data["Volume"]

    close_data.index = pd.to_datetime(close_data.index).tz_localize(None)
    vol_data.index = pd.to_datetime(vol_data.index).tz_localize(None)

    survivors = []
    for t in batch_symbols:
        if t not in close_data.columns or t not in vol_data.columns:
            continue
        p_hist = close_data[t].dropna()
        if len(p_hist) < MIN_HISTORY:
            continue

        v = vol_data[t].dropna().iloc[-63:]
        p = close_data[t].dropna().iloc[-63:]
        common = v.index.intersection(p.index)
        if len(common) < 10:
            continue

        dollar_vol = (v.loc[common] * p.loc[common]).mean()
        if dollar_vol >= MIN_DOLLAR_VOL:
            survivors.append(t)

    return survivors


def run(batch_size=150, max_batches=5, verbose=True):
    """
    Process up to max_batches batches of batch_size each,
    continuing from wherever the last run left off (checkpointed).
    """
    progress = load_progress()
    all_candidates = get_all_appropriate_candidates()
    all_symbols = [c["symbol"] for c in all_candidates]

    remaining = [s for s in all_symbols if s not in progress["processed_symbols"]]

    if verbose:
        print(f"Total appropriate candidates: {len(all_symbols)}")
        print(f"Already processed: {len(progress['processed_symbols'])}")
        print(f"Already validated survivors: {len(progress['validated_survivors'])}")
        print(f"Remaining to process: {len(remaining)}")
        print()

    for batch_num in range(max_batches):
        if not remaining:
            print("All candidates processed.")
            break

        batch = remaining[:batch_size]
        remaining = remaining[batch_size:]

        if verbose:
            print(f"Batch {batch_num+1}/{max_batches}: processing {len(batch)} tickers...")

        t0 = time.time()
        survivors = process_batch(batch, verbose=verbose)
        elapsed = time.time() - t0

        progress["processed_symbols"].extend(batch)
        progress["validated_survivors"].extend(survivors)
        save_progress(progress)

        if verbose:
            print(f"  Survivors this batch: {len(survivors)}/{len(batch)} "
                  f"({len(survivors)/len(batch):.1%}) in {elapsed:.1f}s")
            print(f"  Running total survivors: {len(progress['validated_survivors'])}")
            print()

    return progress


if __name__ == "__main__":
    run(batch_size=150, max_batches=5)
