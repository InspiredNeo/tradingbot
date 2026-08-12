"""
Simulated paper trading portfolio using REAL, live Schwab quote
data, but entirely virtual cash and positions -- no real orders
ever placed. Built because Schwab doesn't offer a genuine paper-
trading sandbox account the way IBKR did; this achieves the same
safe, no-real-money-at-risk testing using real, accurate prices.

All state (virtual cash, virtual positions, trade history) lives
in the same SQLite database as everything else this session, in a
new, dedicated table.
"""
from datetime import datetime
from db_setup import get_connection


def init_simulated_portfolio(starting_cash=1_000_000, reset=False):
    """
    Creates (or resets) the simulated portfolio with a starting
    virtual cash balance. Call reset=True to wipe and restart --
    use with real care, this is destructive.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS simulated_portfolio (
            symbol TEXT PRIMARY KEY,
            shares REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS simulated_cash (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            cash REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS simulated_trade_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            action TEXT,
            shares REAL,
            price REAL,
            total REAL
        )
    """)

    if reset:
        c.execute("DELETE FROM simulated_portfolio")
        c.execute("DELETE FROM simulated_cash")
        c.execute("INSERT INTO simulated_cash (id, cash) VALUES (1, ?)", (starting_cash,))
        print(f"Simulated portfolio RESET with ${starting_cash:,.2f} virtual cash")
    else:
        c.execute("SELECT cash FROM simulated_cash WHERE id = 1")
        existing = c.fetchone()
        if not existing:
            c.execute("INSERT INTO simulated_cash (id, cash) VALUES (1, ?)", (starting_cash,))
            print(f"Simulated portfolio initialized with ${starting_cash:,.2f} virtual cash")
        else:
            print(f"Simulated portfolio already exists with ${existing['cash']:,.2f} cash")

    conn.commit()
    conn.close()


def get_simulated_positions():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT symbol, shares FROM simulated_portfolio WHERE shares > 0")
    positions = {row["symbol"]: row["shares"] for row in c.fetchall()}
    conn.close()
    return positions


def get_simulated_cash():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT cash FROM simulated_cash WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return row["cash"] if row else 0


def get_simulated_total_value(schwab_client):
    """Real, live total value: virtual cash + (virtual shares * REAL current prices)."""
    positions = get_simulated_positions()
    cash = get_simulated_cash()

    if not positions:
        return cash

    prices = schwab_client.get_quotes(list(positions.keys()))
    equity_value = sum(positions[sym] * prices.get(sym, 0) for sym in positions)

    return cash + equity_value


def execute_simulated_trade(symbol, shares, action, price):
    """
    Records a simulated fill using a REAL, live price -- updates
    virtual cash and virtual position, logs the trade. No real
    order ever placed.
    """
    conn = get_connection()
    c = conn.cursor()

    total = shares * price
    c.execute("SELECT cash FROM simulated_cash WHERE id = 1")
    cash = c.fetchone()["cash"]

    if action == "BUY":
        if total > cash:
            conn.close()
            return False, f"Insufficient virtual cash: need ${total:,.2f}, have ${cash:,.2f}"
        new_cash = cash - total
    else:
        new_cash = cash + total

    c.execute("UPDATE simulated_cash SET cash = ? WHERE id = 1", (new_cash,))

    c.execute("SELECT shares FROM simulated_portfolio WHERE symbol = ?", (symbol,))
    existing = c.fetchone()
    current_shares = existing["shares"] if existing else 0
    new_shares = current_shares + shares if action == "BUY" else current_shares - shares

    c.execute("""
        INSERT OR REPLACE INTO simulated_portfolio (symbol, shares)
        VALUES (?, ?)
    """, (symbol, new_shares))

    c.execute("""
        INSERT INTO simulated_trade_log (timestamp, symbol, action, shares, price, total)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), symbol, action, shares, price, total))

    conn.commit()
    conn.close()
    return True, None
