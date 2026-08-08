"""
Save backtest results to the SQL database instead of flat JSON
files. Every run gets a genuinely unique run_id (script name +
timestamp + a short random suffix), making the filename-collision
bug that lost tonight's real baseline results structurally
impossible -- there's no shared filename for two runs to fight
over.
"""
import sqlite3
import uuid
from datetime import datetime
from db_setup import get_connection


def save_backtest_run(script_name, start_date, end_date, results, records):
    """
    results: dict with final_value, sharpe_weekly, max_drawdown,
    calmar, all_gates_passed, and optionally 'notes'.
    records: list of dicts with date, portfolio, dial, scenario
    (the same shape already used throughout adaptive_backtest_v3.py).

    Returns the generated run_id -- print/save this so the run can
    be found again later.
    """
    run_id = f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO backtest_runs
        (run_id, script_name, start_date, end_date, started_at,
         completed_at, final_value, sharpe_weekly, max_drawdown,
         calmar, all_gates_passed, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id, script_name, start_date, end_date,
        results.get("started_at", datetime.now().isoformat()),
        datetime.now().isoformat(),
        results.get("final_value"), results.get("sharpe_weekly"),
        results.get("max_drawdown"), results.get("calmar"),
        1 if results.get("all_gates_passed") else 0,
        results.get("notes", ""),
    ))

    for r in records:
        c.execute("""
            INSERT INTO backtest_weekly_records
            (run_id, date, portfolio_value, dial_value, scenario)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, str(r["date"]), r["portfolio"], r["dial"], r["scenario"]))

    conn.commit()
    conn.close()

    print(f"Saved backtest run: {run_id}")
    print(f"  {len(records)} weekly records saved")
    return run_id


def get_run_by_id(run_id):
    """Retrieve a specific run's metadata + records."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM backtest_runs WHERE run_id = ?", (run_id,))
    run = c.fetchone()

    c.execute("""
        SELECT date, portfolio_value, dial_value, scenario
        FROM backtest_weekly_records WHERE run_id = ? ORDER BY date
    """, (run_id,))
    records = c.fetchall()

    conn.close()
    return dict(run) if run else None, [dict(r) for r in records]


def list_all_runs():
    """List every saved run, most recent first."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT run_id, script_name, final_value, sharpe_weekly,
               completed_at
        FROM backtest_runs ORDER BY completed_at DESC
    """)
    runs = [dict(r) for r in c.fetchall()]
    conn.close()
    return runs


if __name__ == "__main__":
    runs = list_all_runs()
    print(f"Total saved runs: {len(runs)}")
    for r in runs:
        print(f"  {r['run_id']}: {r['script_name']} "
              f"final=${r['final_value']:,.0f}" if r['final_value'] else
              f"  {r['run_id']}: {r['script_name']} (incomplete)")
