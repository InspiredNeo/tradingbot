"""
Quick, real status check for the live paper-trading system --
no digging through logs, just a clear, honest summary of where
things currently stand.
"""
from db_setup import get_connection
from datetime import datetime, timedelta


def check_status():
    conn = get_connection()
    c = conn.cursor()

    print("=" * 60)
    print("PAPER TRADING SYSTEM STATUS")
    print("=" * 60)

    # Most recent regime reading
    c.execute("""
        SELECT date, regime, pct_below, avg_correlation
        FROM live_regime_state ORDER BY date DESC LIMIT 1
    """)
    row = c.fetchone()
    if row:
        print(f"\nMost recent regime check: {row['date']}")
        print(f"  Regime: {row['regime']}")
        print(f"  Breadth: {row['pct_below']:.1%}, Correlation: {row['avg_correlation']:.3f}")

        days_old = (datetime.now().date() - datetime.strptime(row['date'], '%Y-%m-%d').date()).days
        if days_old > 3:
            print(f"  WARNING: last check was {days_old} days ago -- "
                  f"is the scheduled job actually running?")
    else:
        print("\nNo regime data recorded yet.")

    # Recent regime history (real trend, not just latest snapshot)
    c.execute("""
        SELECT date, regime FROM live_regime_state
        ORDER BY date DESC LIMIT 10
    """)
    rows = c.fetchall()
    if rows:
        print(f"\nRecent regime history (last {len(rows)} readings):")
        for r in reversed(rows):
            print(f"  {r['date']}: {r['regime']}")

    # Performance summary
    c.execute("""
        SELECT date, account_value FROM paper_performance_history
        ORDER BY date ASC
    """)
    perf_rows = c.fetchall()
    if perf_rows:
        start_val = perf_rows[0]["account_value"]
        latest_val = perf_rows[-1]["account_value"]
        change = (latest_val - start_val) / start_val
        print(f"\nPerformance since {perf_rows[0]['date']}:")
        print(f"  Start: ${start_val:,.2f}")
        print(f"  Latest ({perf_rows[-1]['date']}): ${latest_val:,.2f}")
        print(f"  Change: {change:+.2%}")
        print(f"  Days tracked: {len(perf_rows)}")
    else:
        print("\nNo performance history recorded yet.")

    conn.close()
    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_status()
