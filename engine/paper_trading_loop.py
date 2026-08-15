"""
Real, live paper-trading loop for the validated regime-based
strategy, using SCHWAB instead of IBKR/IB Gateway. Reuses the
EXACT detection and allocation logic already built and validated
tonight (regime_detector.py, regime_allocation.py).

SWITCHED FROM IBKR TO SCHWAB: IB Gateway proved genuinely unstable
on a headless cloud server -- repeatedly disconnected, and was
found to be tied to the lifetime of whichever terminal/VNC session
started it, defeating the purpose of an always-on server. Schwab's
API is a straightforward REST connection with no persistent
desktop application or virtual display required, genuinely more
appropriate for this use case.
"""
import json
import pandas as pd
from datetime import datetime

from regime_allocation import get_regime_allocation
from schwab_client import get_schwab_client
from simulated_portfolio import (
    get_simulated_positions, get_simulated_cash,
    get_simulated_total_value, execute_simulated_trade,
    init_simulated_portfolio
)

RISK_ASSETS = ["VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF"]
DEF_ASSETS = ["AGG", "TLT", "GLD"]


class PaperTradingLoop:
    def __init__(self):
        self.client = None
        self.connected = False

        (self.breadth_history, self.corr_history, self.regime_history,
         self.prev_severe, self.prev_corr_high) = self._load_state()

    def connect(self):
        self.client = get_schwab_client()
        self.connected = self.client.connected
        return self.connected

    def _load_state(self, lookback_days=60):
        from db_setup import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT date, pct_below, avg_correlation, regime,
                   severely_stressed, corr_high
            FROM live_regime_state
            ORDER BY date ASC
            LIMIT ?
        """, (lookback_days,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            return [], [], [], None, None

        breadth_history = [r["pct_below"] for r in rows]
        corr_history = [r["avg_correlation"] for r in rows]
        regime_history = [r["regime"] for r in rows]
        prev_severe = bool(rows[-1]["severely_stressed"])
        prev_corr_high = bool(rows[-1]["corr_high"])

        print(f"Loaded {len(rows)} days of persisted regime state "
              f"from database (most recent: {rows[-1]['date']})")

        return breadth_history, corr_history, regime_history, prev_severe, prev_corr_high

    def _save_state(self, date, alloc):
        from db_setup import get_connection
        from datetime import datetime as dt
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO live_regime_state
            (date, pct_below, avg_correlation, regime, raw_regime,
             severely_stressed, corr_high, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(date.date()), alloc["pct_below"], alloc["avg_correlation"],
            alloc["regime"], alloc.get("raw_regime", alloc["regime"]),
            int(bool(alloc.get("severely_stressed"))),
            int(bool(alloc.get("corr_high"))),
            dt.now().isoformat(),
        ))
        conn.commit()
        conn.close()

    def get_current_positions(self):
        # SWITCHED to simulated positions -- Schwab has no genuine
        # paper-trading sandbox, so we track virtual positions
        # ourselves while using Schwab's REAL, live prices
        return get_simulated_positions()

    def get_account_value(self):
        return get_simulated_total_value(self.client)

    def run_once(self, px, universe, dry_run=True):
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

        self._save_state(today, alloc)

        equity_target = alloc["equity_target"]
        print(f"Regime: {alloc['regime']}, equity target: {equity_target:.1%}")

        account_value = self.get_account_value()
        current_positions = self.get_current_positions()
        print(f"Account value: ${account_value:,.2f}" if account_value else "Account value: unknown")
        print(f"Current positions: {current_positions}")

        target_dollar_equity = (account_value or 0) * equity_target

        # REAL PORT (Option B, per user's explicit choice): uses the
        # actual, validated SVI + five-model blend from the backtest
        # instead of equal-weight, mapped from the current regime.
        # Deliberately does NOT include the backtest's multi-week
        # rate-limiter or volatility-dial speed adjustment, since
        # daily live checking already provides finer responsiveness
        # than the original weekly backtest needed smoothing for.
        from svi_live_allocation import compute_svi_weights
        print("\nComputing real SVI-based portfolio weights...")
        svi_weights = compute_svi_weights(px, today, RISK_ASSETS, alloc["regime"])

        print(f"\nTarget: ${target_dollar_equity:,.2f} total equity")
        print("Real, SVI-based weights (not equal-weight):")
        for t, w in svi_weights.items():
            print(f"  {t}: {w:.1%} (${target_dollar_equity * w:,.2f})")

        trades_needed = self._compute_trades(
            current_positions, target_dollar_equity, px, today, svi_weights)

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

    def _compute_trades(self, current_positions, target_dollar_equity, px, today, svi_weights):
        # FIXED: was using stale cached historical prices for trade
        # sizing while valuation used live quotes -- now uses live
        # prices throughout. UPDATED: now uses real, per-asset SVI
        # weights instead of an equal split across RISK_ASSETS,
        # porting the actual validated portfolio construction
        # (Option B -- core logic, without the backtest's rate
        # limiter/vol dial).
        live_prices = self.client.get_quotes(RISK_ASSETS)

        trades = {}
        for symbol in RISK_ASSETS:
            price = live_prices.get(symbol)
            if not price:
                price_series = px.loc[:today, symbol].dropna()
                if len(price_series) == 0:
                    continue
                price = float(price_series.iloc[-1])
                print(f"  (using cached price for {symbol}, live quote unavailable)")

            weight = svi_weights.get(symbol, 1.0 / len(RISK_ASSETS))
            asset_target_dollars = target_dollar_equity * weight

            current_shares = current_positions.get(symbol, 0)
            target_shares = asset_target_dollars / price
            shares_delta = target_shares - current_shares

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
        # SWITCHED to simulated fills using REAL, live Schwab
        # prices -- no real orders ever placed
        for symbol, info in trades_needed.items():
            shares = round(abs(info["shares_delta"]))
            if shares == 0:
                continue
            action = "BUY" if info["shares_delta"] > 0 else "SELL"

            success, err = execute_simulated_trade(symbol, shares, action, info["price"])
            if not success:
                print(f"  {symbol}: {action} {shares} shares -- FAILED: {err}")
            else:
                print(f"  {symbol}: {action} {shares} shares -- SIMULATED FILL @ ${info['price']:.2f}")


if __name__ == "__main__":
    import os
    DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    loop = PaperTradingLoop()
    if loop.connect():
        print("Connected to Schwab\n")
        loop.run_once(px, universe, dry_run=True)
    else:
        print("Connection failed")
