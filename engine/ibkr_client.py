"""
IBKR client -- scoped specifically for BACKTESTING RESEARCH data,
not live trading. Schwab remains the live/paper trading broker
(schwab_client.py handles that). This module exists to replace
yfinance as the historical data source, since yfinance is free but
unofficial and rate-limited (hit a real error during universe
building), while IBKR's API is officially supported and free to
use for account holders.

Deliberately does NOT include order placement, rebalancing, or
trade execution methods -- those responsibilities stay with
Schwab. This is a read-only, data-fetching client.
"""
from ib_insync import IB, Stock
import pandas as pd


class IBKRClient:
    def __init__(self, host="127.0.0.1", port=4002, client_id=1):
        """
        port=4002 is IB Gateway's PAPER TRADING port by default.
        Port 4001 is LIVE TRADING -- never use that port for this
        client, since this module has no safeguards against
        accidentally touching a live account (it isn't meant to).
        """
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib = IB()
        self.connected = False

    def connect(self):
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            self.ib.reqMarketDataType(3)  # delayed data, no paid
                                            # subscription required
            self.connected = self.ib.isConnected()
            return self.connected
        except Exception as e:
            print(f"IBKR connection failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.connected:
            self.ib.disconnect()
            self.connected = False

    def get_historical_bars(self, symbol, duration="20 Y", bar_size="1 day"):
        """
        Fetch real historical daily bars for a single ticker.

        duration: IBKR format, e.g. "20 Y", "1 Y", "6 M"
        bar_size: e.g. "1 day", "1 week"

        Returns a pandas DataFrame with columns: date, open, high,
        low, close, volume -- or None if the request fails.
        """
        if not self.connected:
            print("Not connected -- call connect() first")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")
            self.ib.qualifyContracts(contract)

            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow="TRADES",
                useRTH=True,
            )

            if not bars:
                return None

            df = pd.DataFrame([{
                "date": b.date, "open": b.open, "high": b.high,
                "low": b.low, "close": b.close, "volume": b.volume,
            } for b in bars])
            return df

        except Exception as e:
            print(f"Historical data fetch failed for {symbol}: {e}")
            return None


    def get_bulk_historical(self, symbols, duration="20 Y",
                            bar_size="1 day", pause_seconds=1.0,
                            verbose=True):
        """
        Fetch historical bars for MANY symbols, one at a time (IBKR's
        real constraint, same as Schwab -- no bulk endpoint), with
        real pacing between requests. Returns a dict of {symbol: df}.

        Same disciplined batching/pacing pattern already proven
        reliable throughout this session (build_full_universe.py,
        universe_refresh.py) -- avoids overwhelming the connection
        with rapid-fire requests.
        """
        import time
        results = {}
        failed = []

        for i, symbol in enumerate(symbols):
            df = self.get_historical_bars(symbol, duration=duration,
                                          bar_size=bar_size)
            if df is not None and len(df) > 0:
                results[symbol] = df
            else:
                failed.append(symbol)

            if verbose and (i + 1) % 10 == 0:
                pct = (i + 1) / len(symbols) * 100
                print(f"  {pct:.1f}%  {i+1}/{len(symbols)}  "
                      f"succeeded={len(results)}  failed={len(failed)}")

            time.sleep(pause_seconds)

        if verbose:
            print(f"\nFinal: {len(results)} succeeded, {len(failed)} failed")
            if failed:
                print(f"Failed symbols: {failed[:20]}"
                      f"{'...' if len(failed) > 20 else ''}")

        return results, failed


if __name__ == "__main__":
    client = IBKRClient()
    if client.connect():
        print(f"Connected: {client.connected}")
        df = client.get_historical_bars("VTI", duration="1 Y")
        if df is not None:
            print(f"Fetched {len(df)} bars for VTI")
            print(df.head())
            print(df.tail())
        client.disconnect()
    else:
        print("Connection failed")
