"""
SQLite data management layer -- replaces scattered flat files
(bt_prices.parquet, universe JSON files, timestamped backtest
result JSONs) with real, queryable structured storage.

Does NOT replace the price data format itself (parquet stays,
it's genuinely efficient for the large price matrix) -- this
specifically targets the things that were scattered, hard to
query, and (as happened tonight) easy to accidentally overwrite:
universe membership, backtest run metadata/results, and ticker
validation status.
"""
import sqlite3
import os
import json
from datetime import datetime

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
DB_PATH = os.path.join(DATA_DIR, "tradingbot.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # access columns by name
    return conn


def init_schema():
    conn = get_connection()
    c = conn.cursor()

    # Universe: every ticker we've evaluated, with its validation
    # status and metadata -- replaces final_equity_universe.json
    # and universe_build_progress.json
    c.execute("""
        CREATE TABLE IF NOT EXISTS universe (
            ticker TEXT PRIMARY KEY,
            description TEXT,
            asset_type TEXT,
            first_seen_date TEXT,
            history_days INTEGER,
            avg_dollar_volume REAL,
            is_equity INTEGER,
            is_validated INTEGER,
            excluded_reason TEXT,
            added_at TEXT
        )
    """)

    # Backtest runs: every run's metadata and final metrics --
    # replaces the scattered, collision-prone timestamped JSON
    # files. The run_id is a real, unique identifier so runs can
    # NEVER silently overwrite each other the way tonight's bug did.
    c.execute("""
        CREATE TABLE IF NOT EXISTS backtest_runs (
            run_id TEXT PRIMARY KEY,
            script_name TEXT,
            start_date TEXT,
            end_date TEXT,
            started_at TEXT,
            completed_at TEXT,
            final_value REAL,
            sharpe_weekly REAL,
            max_drawdown REAL,
            calmar REAL,
            all_gates_passed INTEGER,
            notes TEXT
        )
    """)

    # Weekly records: the actual week-by-week series for each run
    # -- replaces the "records" list inside each JSON file, but
    # queryable across runs (e.g. "show me every run's value on
    # 2008-10-03" becomes one real SQL query instead of opening
    # N separate files)
    c.execute("""
        CREATE TABLE IF NOT EXISTS backtest_weekly_records (
            run_id TEXT,
            date TEXT,
            portfolio_value REAL,
            dial_value REAL,
            scenario TEXT,
            FOREIGN KEY (run_id) REFERENCES backtest_runs(run_id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Schema initialized at {DB_PATH}")


if __name__ == "__main__":
    init_schema()
