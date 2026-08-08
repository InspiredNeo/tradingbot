"""
Schwab API integration for Market Terminal.
Handles OAuth, token refresh, account data, and order execution.
"""
import os
import json
import time
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))

SCHWAB_CLIENT_ID = os.getenv("SCHWAB_CLIENT_ID")
SCHWAB_CLIENT_SECRET = os.getenv("SCHWAB_CLIENT_SECRET")
SCHWAB_CALLBACK_URL = "https://127.0.0.1:8182"
TOKEN_FILE = os.path.expanduser("~/tradingbot/config/schwab_tokens.json")
STATUS_FILE = os.path.expanduser("~/tradingbot/config/schwab_status.json")


class SchwabClient:
    def __init__(self):
        self.client = None
        self.connected = False
        self.account_hash = None
        self._refresh_thread = None
        self._load_status()

    # ---------- Connection ----------
    def connect(self):
        """
        Initiate OAuth flow. Opens browser for user login.
        Called once manually — after that tokens auto-refresh.
        """
        try:
            import schwab
            self.client = schwab.auth.client_from_login_flow(
                api_key=SCHWAB_CLIENT_ID,
                app_secret=SCHWAB_CLIENT_SECRET,
                callback_url=SCHWAB_CALLBACK_URL,
                token_path=TOKEN_FILE,
            )
            self.connected = True
            self._load_account_hash()
            self._start_refresh_thread()
            self._save_status(connected=True)
            print("Schwab connected successfully")
            return True
        except Exception as e:
            print(f"Schwab connection failed: {e}")
            self._save_status(connected=False, error=str(e))
            return False

    def reconnect_from_token(self):
        """
        Reconnect using saved token file (no browser needed).
        Used on app restart if tokens are still valid.
        """
        try:
            import schwab
            if not os.path.exists(TOKEN_FILE):
                return False
            self.client = schwab.auth.client_from_token_file(
                token_path=TOKEN_FILE,
                api_key=SCHWAB_CLIENT_ID,
                app_secret=SCHWAB_CLIENT_SECRET,
            )
            self.connected = True
            self._load_account_hash()
            self._start_refresh_thread()
            self._save_status(connected=True)
            print("Schwab reconnected from saved token")
            return True
        except Exception as e:
            print(f"Schwab token reconnect failed: {e}")
            self.connected = False
            return False

    def disconnect(self):
        self.connected = False
        self.client = None
        if self._refresh_thread:
            self._refresh_thread = None
        self._save_status(connected=False)

    # ---------- Account Data ----------
    def get_account_balance(self):
        """Returns total account value, cash, and buying power."""
        if not self.connected or not self.client:
            return None
        try:
            resp = self.client.get_account(
                self.account_hash,
                fields=[self.client.Account.Fields.POSITIONS]
            )
            data = resp.json()
            current = data.get("securitiesAccount", {}).get("currentBalances", {})
            return {
                "total_value": current.get("liquidationValue", 0),
                "cash": current.get("cashBalance", 0),
                "buying_power": current.get("buyingPower", 0),
                "day_pnl": current.get("dayProfitLoss", 0),
                "day_pnl_pct": current.get("dayProfitLossPercentage", 0),
            }
        except Exception as e:
            print(f"Balance fetch failed: {e}")
            return None

    def get_positions(self):
        """Returns list of current positions."""
        if not self.connected or not self.client:
            return []
        try:
            resp = self.client.get_account(
                self.account_hash,
                fields=[self.client.Account.Fields.POSITIONS]
            )
            data = resp.json()
            raw_positions = data.get("securitiesAccount", {}).get("positions", [])
            positions = []
            for p in raw_positions:
                instrument = p.get("instrument", {})
                positions.append({
                    "symbol": instrument.get("symbol", ""),
                    "asset_type": instrument.get("assetType", ""),
                    "quantity": p.get("longQuantity", 0),
                    "market_value": p.get("marketValue", 0),
                    "average_price": p.get("averagePrice", 0),
                    "day_pnl": p.get("currentDayProfitLoss", 0),
                    "unrealized_pnl": p.get("unrealizedProfitLoss", 0),
                    "unrealized_pnl_pct": p.get("unrealizedProfitLossPercentage", 0),
                })
            return positions
        except Exception as e:
            print(f"Positions fetch failed: {e}")
            return []

    def search_instruments_by_description(self, search_term, max_results=None):
        """
        Search for instruments by description regex, e.g. searching
        for "ETF" in the description field to find a broad batch of
        ETF tickers in one call, rather than needing to already
        know each symbol in advance.

        Returns a list of dicts: symbol, description, asset_type,
        exchange -- or empty list on any failure (connection issue,
        no matches, API error). Never raises -- same fail-safe
        pattern as get_positions() above.
        """
        if not self.connected or not self.client:
            return []
        try:
            resp = self.client.get_instruments(
                search_term,
                projection=self.client.Instrument.Projection.DESCRIPTION_REGEX
            )
            data = resp.json()
            instruments = data.get("instruments", [])
            results = []
            for inst in instruments:
                results.append({
                    "symbol": inst.get("symbol", ""),
                    "description": inst.get("description", ""),
                    "asset_type": inst.get("assetType", ""),
                    "exchange": inst.get("exchange", ""),
                })
            if max_results:
                results = results[:max_results]
            return results
        except Exception as e:
            print(f"Instrument search failed: {e}")
            return []

    def get_portfolio_summary(self):
        """Returns combined balance + positions for the terminal."""
        balance = self.get_account_balance()
        positions = self.get_positions()
        return {
            "balance": balance,
            "positions": positions,
            "last_sync": datetime.now().isoformat(),
            "connected": self.connected,
        }

    def sync_to_portfolio_file(self):
        """
        Sync real Schwab positions to portfolio.json.
        This auto-populates the Portfolio tab.
        """
        positions = self.get_positions()
        if not positions:
            return False
        portfolio = []
        for p in positions:
            if p["asset_type"] in ("EQUITY", "ETF") and p["quantity"] > 0:
                portfolio.append({
                    "symbol": p["symbol"],
                    "shares": p["quantity"],
                    "cost_basis": p["average_price"],
                    "source": "schwab",
                })
        pf_file = os.path.expanduser("~/tradingbot/config/portfolio.json")
        with open(pf_file, "w") as f:
            json.dump(portfolio, f, indent=2)
        print(f"Synced {len(portfolio)} positions from Schwab")
        return True

    # ---------- Order Execution ----------
    def place_market_order(self, symbol, quantity, instruction="BUY"):
        """
        Place a market order.
        instruction: "BUY" or "SELL"
        """
        if not self.connected or not self.client:
            return None, "Not connected"
        try:
            from schwab.orders.equities import equity_buy_market, equity_sell_market
            if instruction == "BUY":
                order = equity_buy_market(symbol, quantity)
            else:
                order = equity_sell_market(symbol, quantity)
            resp = self.client.place_order(self.account_hash, order)
            order_id = resp.headers.get("location", "").split("/")[-1]
            self._log_trade(symbol, instruction, quantity, "MARKET", order_id)
            return order_id, None
        except Exception as e:
            return None, str(e)

    def place_limit_order(self, symbol, quantity, price, instruction="BUY"):
        """
        Place a limit order just inside the bid-ask spread.
        instruction: "BUY" or "SELL"
        """
        if not self.connected or not self.client:
            return None, "Not connected"
        try:
            from schwab.orders.equities import equity_buy_limit, equity_sell_limit
            if instruction == "BUY":
                order = equity_buy_limit(symbol, quantity, price)
            else:
                order = equity_sell_limit(symbol, quantity, price)
            resp = self.client.place_order(self.account_hash, order)
            order_id = resp.headers.get("location", "").split("/")[-1]
            self._log_trade(symbol, instruction, quantity, "LIMIT", order_id, price)
            return order_id, None
        except Exception as e:
            return None, str(e)

    def cancel_order(self, order_id):
        """Cancel an open order."""
        if not self.connected or not self.client:
            return False
        try:
            self.client.cancel_order(order_id, self.account_hash)
            return True
        except Exception:
            return False

    def get_order_status(self, order_id):
        """Check status of an order."""
        if not self.connected or not self.client:
            return None
        try:
            resp = self.client.get_order(order_id, self.account_hash)
            data = resp.json()
            return {
                "order_id": order_id,
                "status": data.get("status"),
                "filled_quantity": data.get("filledQuantity", 0),
                "price": data.get("price", 0),
            }
        except Exception:
            return None

    def execute_rebalance(self, target_weights, budget, dry_run=False):
        """
        Execute a full rebalance.
        target_weights: {"VTI": 0.6, "SCHF": 0.3, "BND": 0.1}
        budget: total amount to invest
        dry_run: if True, just logs what would happen without placing orders
        Returns list of orders placed.
        """
        import yfinance as yf
        orders = []
        errors = []

        # Get current prices
        prices = {}
        for sym in target_weights:
            try:
                hist = yf.Ticker(sym).history(period="1d")
                if not hist.empty:
                    prices[sym] = float(hist["Close"].iloc[-1])
            except Exception:
                errors.append(f"Could not fetch price for {sym}")

        if not prices:
            return [], ["Could not fetch any prices"]

        # Calculate target dollar amounts and shares
        for sym, weight in target_weights.items():
            if sym not in prices:
                continue
            target_dollars = budget * weight
            target_shares = target_dollars / prices[sym]
            # Round down to whole shares (ETFs don't require fractional)
            shares = int(target_shares)
            if shares < 1:
                continue

            actual_cost = shares * prices[sym]
            # Use limit order just inside bid-ask (0.01% below ask for buys)
            limit_price = round(prices[sym] * 1.001, 2)

            if dry_run:
                orders.append({
                    "symbol": sym,
                    "action": "BUY",
                    "shares": shares,
                    "price": prices[sym],
                    "total": actual_cost,
                    "status": "DRY RUN",
                })
            else:
                order_id, err = self.place_limit_order(sym, shares, limit_price, "BUY")
                if err:
                    errors.append(f"{sym}: {err}")
                else:
                    orders.append({
                        "symbol": sym,
                        "action": "BUY",
                        "shares": shares,
                        "price": limit_price,
                        "total": shares * limit_price,
                        "order_id": order_id,
                        "status": "PLACED",
                    })

        return orders, errors

    def hard_sell_all(self, reason="Manual hard sell"):
        """
        Sell all positions immediately.
        Sends Slack notification and locks the bot.
        """
        positions = self.get_positions()
        if not positions:
            return [], "No positions to sell"

        sold = []
        errors = []
        import yfinance as yf

        for p in positions:
            sym = p["symbol"]
            qty = p["quantity"]
            if qty <= 0:
                continue
            try:
                price = float(yf.Ticker(sym).history(period="1d")["Close"].iloc[-1])
            except Exception:
                price = p.get("market_value", 0) / qty if qty else 0

            order_id, err = self.place_market_order(sym, qty, "SELL")
            if err:
                errors.append(f"{sym}: {err}")
            else:
                sold.append((sym, qty, price))

        # Notify via Slack
        if sold:
            try:
                import sys
                sys.path.append(os.path.expanduser("~/tradingbot/dashboard"))
                from slack_utils import send_hard_sell
                total = sum(qty * price for _, qty, price in sold)
                send_hard_sell(sold, total, [reason])
            except Exception:
                pass

            # Lock the bot
            config_file = os.path.expanduser("~/tradingbot/config/bot_config.json")
            try:
                with open(config_file) as f:
                    config = json.load(f)
                config["active"] = False
                config["locked"] = True
                config["lock_reason"] = reason
                config["lock_time"] = datetime.now().isoformat()
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=2)
            except Exception:
                pass

        return sold, errors

    # ---------- Internal helpers ----------
    def _load_account_hash(self):
        """Get the account hash needed for API calls."""
        try:
            resp = self.client.get_account_numbers()
            accounts = resp.json()
            if accounts:
                self.account_hash = accounts[0].get("hashValue")
                print(f"Account loaded: {self.account_hash[:8]}...")
        except Exception as e:
            print(f"Could not load account hash: {e}")

    def _start_refresh_thread(self):
        """Start background thread to keep tokens fresh."""
        def _refresh_loop():
            while self.connected:
                time.sleep(1500)  # refresh every 25 minutes (tokens last 30)
                try:
                    if self.client:
                        # schwab-py handles refresh automatically
                        # just make a lightweight API call to trigger it
                        self.client.get_account_numbers()
                        self._save_status(connected=True,
                                         last_refresh=datetime.now().isoformat())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    # Try to reconnect from saved token
                    self.reconnect_from_token()

        self._refresh_thread = threading.Thread(target=_refresh_loop, daemon=True)
        self._refresh_thread.start()

    def _save_status(self, connected=False, error=None, last_refresh=None):
        try:
            status = {
                "connected": connected,
                "account_hash": self.account_hash[:8] + "..." if self.account_hash else None,
                "last_refresh": last_refresh or datetime.now().isoformat(),
                "error": error,
            }
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f, indent=2)
        except Exception:
            pass

    def _load_status(self):
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE) as f:
                    status = json.load(f)
                self.connected = status.get("connected", False)
        except Exception:
            pass

    def _log_trade(self, symbol, action, quantity, order_type, order_id, price=None):
        """Log trade to bot_log.json."""
        log_file = os.path.expanduser("~/tradingbot/config/bot_log.json")
        try:
            log = []
            if os.path.exists(log_file):
                with open(log_file) as f:
                    log = json.load(f)
            log.append({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": symbol,
                "action": action,
                "shares": quantity,
                "price": price,
                "order_type": order_type,
                "order_id": order_id,
                "model": "manual",
            })
            with open(log_file, "w") as f:
                json.dump(log, f, indent=2)
        except Exception:
            pass


# Singleton instance
_schwab = None


def get_schwab_client():
    global _schwab
    if _schwab is None:
        _schwab = SchwabClient()
        # Try to reconnect from saved token on startup
        if os.path.exists(TOKEN_FILE):
            _schwab.reconnect_from_token()
    return _schwab
