"""
Master signal collector - combines all 4 signal modules.
Returns unified 58-feature vector for regime detection.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_all_signals(verbose=False):
    """
    Fetch all 4 signal modules in parallel.
    Returns (results_dict, 58-feature vector)
    """
    from signals.market_signals import get_all_market_signals
    from signals.momentum_signals import get_all_momentum_signals
    from signals.sentiment_signals import get_all_sentiment_signals
    from signals.macro_signals import get_all_macro_signals

    results = {}
    vectors = {}

    signal_fns = {
        "market": get_all_market_signals,
        "momentum": get_all_momentum_signals,
        "sentiment": get_all_sentiment_signals,
        "macro": get_all_macro_signals,
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fn): name
                   for name, fn in signal_fns.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                r, v = future.result()
                results[name] = r
                vectors[name] = v
            except Exception as e:
                print(f"  Signal error ({name}): {e}")

    # Concatenate all vectors
    full_vector = np.concatenate([
        vectors.get("market", np.zeros(16)),
        vectors.get("momentum", np.zeros(14)),
        vectors.get("sentiment", np.zeros(12)),
        vectors.get("macro", np.zeros(16)),
    ]).astype(np.float32)

    if verbose:
        print(f"\nFull signal vector: {full_vector.shape[0]} features")
        print(f"Market:    {vectors.get('market', []).shape}")
        print(f"Momentum:  {vectors.get('momentum', []).shape}")
        print(f"Sentiment: {vectors.get('sentiment', []).shape}")
        print(f"Macro:     {vectors.get('macro', []).shape}")

    return results, full_vector


if __name__ == "__main__":
    print("Fetching all signals...")
    t = time.time()
    results, vector = get_all_signals(verbose=True)
    print(f"\nTotal fetch time: {time.time()-t:.2f}s")
    print(f"Feature vector shape: {vector.shape}")
    print(f"Min: {vector.min():.3f} Max: {vector.max():.3f} Mean: {vector.mean():.3f}")
