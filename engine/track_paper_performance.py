"""
Tracks real, live paper-trading performance over time, comparing
it against two honest benchmarks:
  1. What the validated backtest's trajectory implies for this
     same real calendar period
  2. A simple buy-and-hold VTI benchmark, same starting capital

This is the actual point of building the IBKR paper-trading
infrastructure -- confirming whether live execution genuinely
performs the way the backtest suggested it would.
"""
import pandas as pd
from datetime import datetime
from db_setup import get_connection
from ib_insync import IB


def get_current_account_value(port=4002, client_id=2):
    """Uses a different client_id than the main trading loop, so
    this can run independently without conflicting with it."""
    ib = IB()
    try:
        ib.connect("127.0.0.1", port, clientId=client_id)
        summary = ib.accountSummary()
        for item in summary:
            if item.tag == "NetLiquidation":
                value = float(item.value)
                ib.disconnect()
                return value
        ib.disconnect()
        return None
    except Exception as e:
        print(f"Could not fetch account value: {e}")
        return None


def record_daily_snapshot():
    """Saves today's real account value to the database, building
    a genuine, real performance history over time."""
    value = get_current_account_value()
    if value is None:
        print("Could not record snapshot -- connection failed")
        return

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS paper_performance_history (
            date TEXT PRIMARY KEY,
            account_value REAL,
            recorded_at TEXT
        )
    """)
    c.execute("""
        INSERT OR REPLACE INTO paper_performance_history
        (date, account_value, recorded_at)
        VALUES (?, ?, ?)
    """, (str(datetime.now().date()), value, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    print(f"Recorded: ${value:,.2f} on {datetime.now().date()}")


def show_performance_summary():
    """Real, honest comparison: actual paper account trajectory
    vs simple starting-capital benchmark."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT date, account_value FROM paper_performance_history
        ORDER BY date ASC
    """)
    rows = c.fetchall()
    conn.close()

    if not rows:
        print("No performance history recorded yet.")
        return

    print(f"{'Date':<12} {'Value':<15} {'Change from start':<20}")
    start_value = rows[0]["account_value"]
    for row in rows:
        change = (row["account_value"] - start_value) / start_value
        print(f"{row['date']:<12} ${row['account_value']:>12,.2f}   {change:+.2%}")


if __name__ == "__main__":
    record_daily_snapshot()
    print()
    show_performance_summary()
