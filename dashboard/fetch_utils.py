"""
Parallel data fetching utilities.
Uses ThreadPoolExecutor to fetch multiple tickers simultaneously.
"""
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed
from cache_utils import mem_get, mem_set, cache_get, cache_set


def fetch_ticker_info(sym):
    """Fetch ticker info with memory cache."""
    cached = mem_get(f"info:{sym}")
    if cached:
        return sym, cached
    try:
        info = yf.Ticker(sym).info
        mem_set(f"info:{sym}", info)
        return sym, info
    except Exception:
        return sym, {}


def fetch_ticker_history(sym, period="1y"):
    """Fetch price history with disk cache."""
    cache_key = f"history:{sym}:{period}"
    cached = cache_get(cache_key, ttl=900)
    if cached:
        import pandas as pd
        return sym, pd.Series(cached["values"], index=pd.to_datetime(cached["index"]))
    try:
        hist = yf.Ticker(sym).history(period=period)
        close = hist["Close"].dropna()
        cache_set(cache_key, {
            "values": close.tolist(),
            "index": [str(i) for i in close.index],
        }, ttl=900)
        return sym, close
    except Exception:
        return sym, None


def fetch_many_info(symbols, max_workers=10):
    """Fetch info for multiple tickers in parallel."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_ticker_info, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym, info = future.result()
            results[sym] = info
    return results


def fetch_many_history(symbols, period="1y", max_workers=8):
    """Fetch price history for multiple tickers in parallel."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_ticker_history, sym, period): sym
                   for sym in symbols}
        for future in as_completed(futures):
            sym, hist = future.result()
            results[sym] = hist
    return results


def fetch_current_prices(symbols):
    """Fast batch price fetch using yfinance download."""
    cache_key = f"prices:{':'.join(sorted(symbols))}"
    cached = mem_get(cache_key, ttl=60)  # 1 minute cache for prices
    if cached:
        return cached
    try:
        import yfinance as yf
        if len(symbols) == 1:
            hist = yf.Ticker(symbols[0]).history(period="5d")
            prices = {symbols[0]: float(hist["Close"].dropna().iloc[-1])} if not hist.empty else {}
        else:
            data = yf.download(symbols, period="2d", progress=False, group_by="ticker")
            prices = {}
            for sym in symbols:
                try:
                    closes = data[sym]["Close"].dropna()
                    if not closes.empty:
                        prices[sym] = float(closes.iloc[-1])
                except Exception:
                    pass
        mem_set(cache_key, prices)
        return prices
    except Exception:
        return {}
