"""
Real, live paper-trading loop for the validated regime-based
strategy. Reuses the EXACT detection and allocation logic already
built and validated tonight (regime_detector.py, regime_allocation.py)
-- no new strategy logic, just wiring proven code to real IBKR
paper execution.

Deliberately simple for a first real version: checks current
regime, computes target equity allocation, compares to actual
current holdings, and places real (paper) orders to close the gap.
Meant to be run on a schedule (e.g. daily), not continuously.
"""
import json
import pandas as pd
from datetime import datetime
from ib_insync import IB, Stock, MarketOrder

from regime_allocation import get_regime_allocation

RISK_ASSETS = ["VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF"]
DEF_ASSETS = ["AGG", "TLT", "GLD"]


class PaperTradingLoop:
    def __init__(self, port=4002, client_id=1):
        self.ib = IB()
        self.port = port
        self.client_id = client_id
        self.connected = False

        # State that needs to persist across real runs -- for a
        # true live system this would be saved to the database
        # built earlier tonight, not just in-memory
        self.breadth_history = []
        self.corr_history = []
        self.regime_history = []
        self.prev_severe = None
        self.prev_corr_high = None

    def connect(self):
        self.ib.connect("127.0.0.1", self.port, clientId=self.client_id)
        self.ib.reqMarketDataType(3)
        self.connected = self.ib.isConnected()
        return self.connected

    def get_current_positions(self):
        positions = self.ib.positions()
        return {p.contract.symbol: p.position for p in positions}

    def get_account_value(self):
        summary = self.ib.accountSummary()
        for item in summary:
            if item.tag == "NetLiquidation":
                return float(item.value)
        return None

    def run_once(self, px, universe, dry_run=True):
        """
        One real cycle: check regime, compute target, compare to
        actual holdings, place orders to close the gap.

        dry_run=True: compute and print the real intended trades
        WITHOUT actually placing them -- always start here.
        """
        today = pd.Timestamp(datetime.now().date())

        alloc = get_regime_allocation(
            px, today, universe,
            breadth_history=self.breadth_history,
            previously_severe=self.prev_severe,
            corr_history=self.corr_history,
            previously_corr_high=self.prev_corr_high,
            regime_history=self.regime_history)

        if alloc is None:
            print("Regime detection failed -- no action taken")
            return

        self.breadth_history.append(alloc["pct_below"])
        self.prev_severe = alloc.get("severely_stressed")
        self.corr_history.append(alloc["avg_correlation"])
        self.prev_corr_high = alloc.get("corr_high")
        self.regime_history.append(alloc["regime"])

        equity_target = alloc["equity_target"]
        print(f"Regime: {alloc['regime']}, equity target: {equity_target:.1%}")

        account_value = self.get_account_value()
        current_positions = self.get_current_positions()
        print(f"Account value: ${account_value:,.2f}" if account_value else "Account value: unknown")
        print(f"Current positions: {current_positions}")

        # Simple, equal-weight split across RISK_ASSETS for the
        # equity portion -- a real production version would reuse
        # the full SVI-based construction from the backtest, this
        # is deliberately simplified for the first live version
        target_dollar_equity = (account_value or 0) * equity_target
        per_asset_target = target_dollar_equity / len(RISK_ASSETS)

        print(f"\nTarget: ${target_dollar_equity:,.2f} total equity "
              f"(${per_asset_target:,.2f} per asset across {len(RISK_ASSETS)} assets)")

        # Compute real, specific per-asset trades needed to close
        # the gap between current holdings and the target allocation
        trades_needed = self._compute_trades(
            current_positions, per_asset_target, px, today)

        print("\nTrades needed:")
        for symbol, info in trades_needed.items():
            action = "BUY" if info["shares_delta"] > 0 else "SELL"
            print(f"  {symbol}: {action} {abs(info['shares_delta']):.0f} shares "
                  f"(current: {info['current_shares']:.0f}, "
                  f"target: {info['target_shares']:.0f}, "
                  f"price: ${info['price']:.2f})")

        if dry_run:
            print("\n[DRY RUN] No real orders placed.")
        else:
            print("\n[LIVE PAPER] Placing real orders...")
            self._execute_trades(trades_needed)

    def _compute_trades(self, current_positions, per_asset_target, px, today):
        """
        For each risk asset, compute the real share-count delta
        needed to move from current holdings to the target dollar
        allocation. Uses the most recent real price available.
        """
        trades = {}
        for symbol in RISK_ASSETS:
            if symbol not in px.columns:
                continue
            price_series = px.loc[:today, symbol].dropna()
            if len(price_series) == 0:
                continue
            price = float(price_series.iloc[-1])

            current_shares = current_positions.get(symbol, 0)
            target_shares = per_asset_target / price
            shares_delta = target_shares - current_shares

            # Only trade if the gap is meaningful -- avoid placing
            # tiny, cost-inefficient orders for rounding-level
            # differences (same principle as the min_trade threshold
            # already used throughout the real backtest logic)
            MIN_TRADE_DOLLARS = 100
            if abs(shares_delta * price) < MIN_TRADE_DOLLARS:
                continue

            trades[symbol] = {
                "current_shares": current_shares,
                "target_shares": target_shares,
                "shares_delta": shares_delta,
                "price": price,
            }
        return trades

    def _execute_trades(self, trades_needed):
        """
        Place REAL (paper) market orders for each computed trade.
        Only called when dry_run=False -- worth extra caution here
        since this is the one function that actually moves money,
        even paper money.
        """
        for symbol, info in trades_needed.items():
            shares = round(abs(info["shares_delta"]))
            if shares == 0:
                continue
            action = "BUY" if info["shares_delta"] > 0 else "SELL"

            contract = Stock(symbol, "SMART", "USD")
            self.ib.qualifyContracts(contract)
            order = MarketOrder(action, shares)
            trade = self.ib.placeOrder(contract, order)
            self.ib.sleep(2)

            print(f"  {symbol}: {action} {shares} shares -- "
                  f"status: {trade.orderStatus.status}")


if __name__ == "__main__":
    import os
    DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    loop = PaperTradingLoop()
    if loop.connect():
        print("Connected to IBKR paper account\n")
        loop.run_once(px, universe, dry_run=True)
        loop.ib.disconnect()
    else:
        print("Connection failed")
