"""
Standalone, lightweight background poller -- connects to IBKR
every few minutes and writes fresh portfolio value snapshots to
the database. Runs as its own separate process, NOT inside Dash's
callback threading, avoiding the asyncio/threading incompatibility
found and worked around earlier tonight.

Meant to run continuously in the background during market hours,
separate from both the Dash dashboard and the once-daily scheduled
trading loop.
"""
import time
from datetime import datetime
from ib_insync import IB
from db_setup import get_connection


def poll_once(client_id=4):
    ib = IB()
    try:
        ib.connect("127.0.0.1", 4002, clientId=client_id, timeout=5)
        summary = ib.accountSummary()
        value = None
        for item in summary:
            if item.tag == "NetLiquidation":
                value = float(item.value)
        ib.disconnect()

        if value is None:
            print(f"[{datetime.now()}] Could not read account value")
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
    print(f"Starting live value poller, polling every {interval_seconds}s")
    while True:
        poll_once()
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_continuous(interval_seconds=120)
