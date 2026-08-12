"""
Standalone, lightweight background poller -- connects to Schwab
every few minutes and writes fresh, real portfolio value snapshots
to the database. Runs as its own separate process.

SWITCHED FROM IBKR TO SCHWAB tonight -- see paper_trading_loop.py
for the real reasoning (Gateway proved genuinely unreliable on a
headless cloud server).
"""
import time
from datetime import datetime
from schwab_client import get_schwab_client
from simulated_portfolio import get_simulated_total_value
from db_setup import get_connection


def poll_once():
    try:
        client = get_schwab_client()
        if not client.connected:
            print(f"[{datetime.now()}] Schwab not connected")
            return

        value = get_simulated_total_value(client)
        if value is None:
            print(f"[{datetime.now()}] Could not compute portfolio value")
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS live_value_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                account_value REAL
            )
        """)
        c.execute("""
            INSERT INTO live_value_snapshots (timestamp, account_value)
            VALUES (?, ?)
        """, (datetime.now().isoformat(), value))
        conn.commit()
        conn.close()

        print(f"[{datetime.now()}] Recorded: ${value:,.2f}")

    except Exception as e:
        print(f"[{datetime.now()}] Poll failed: {e}")


def run_continuous(interval_seconds=120):
    """Runs forever, polling every interval_seconds (default 2 min)."""
    print(f"Starting live value poller (Schwab), polling every {interval_seconds}s")
    while True:
        poll_once()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_continuous(interval_seconds=120)
