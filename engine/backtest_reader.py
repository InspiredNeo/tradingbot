"""
Reads backtest log files and results for dashboard display.
Safe to read while a backtest is still actively running --
never writes to these files, only reads.
"""
import os
import re
import json
import glob
from datetime import datetime

ENGINE_DIR = os.path.expanduser("~/tradingbot/engine")
DATA_DIR = os.path.join(ENGINE_DIR, "histdata")

LINE_PATTERN = re.compile(
    r'(\d{4}-\d{2}-\d{2})\s+\$\s*([\d,]+)\s+dial=([\d.]+)\s+scen=(\S+)'
)


def parse_live_log(log_filename, max_points=2000):
    """
    Parse a running (or completed) backtest log file.
    Returns a list of dicts: date, value, dial, scenario.
    Safe against partial/mid-write lines -- just skips them.

    max_points caps how many rows we return (most recent),
    since a full 22-year weekly backtest has ~1150 rows and
    we don't want to ship the whole thing to the browser if
    someone's just checking progress.
    """
    log_path = os.path.join(ENGINE_DIR, log_filename)
    if not os.path.exists(log_path):
        return []

    records = []
    try:
        with open(log_path, encoding='utf-8', errors='ignore') as f:
            for line in f:
                m = LINE_PATTERN.search(line)
                if m:
                    date_str, val_str, dial_str, scen = m.groups()
                    try:
                        records.append({
                            "date": date_str,
                            "value": float(val_str.replace(',', '')),
                            "dial": float(dial_str),
                            "scenario": scen,
                        })
                    except ValueError:
                        continue  # skip malformed/partial line
    except Exception:
        return records  # return whatever we got before any read error

    if len(records) > max_points:
        records = records[-max_points:]
    return records


def is_backtest_running(process_name="adaptive_backtest_v3.py"):
    """
    Check if a backtest process is currently running, using ps.
    Best-effort -- returns False if the check itself fails.
    """
    try:
        import subprocess
        result = subprocess.run(
            ["pgrep", "-f", process_name],
            capture_output=True, text=True, timeout=3
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def list_available_backtests():
    """
    Find all saved backtest result JSON files plus any live logs,
    so the dashboard can offer a picker.
    """
    results = []

    # Completed JSON results
    for path in glob.glob(os.path.join(DATA_DIR, "*backtest*.json")):
        name = os.path.basename(path)
        try:
            with open(path) as f:
                data = json.load(f)
            results.append({
                "name": name,
                "type": "completed",
                "path": path,
                "final": data.get("final"),
                "sharpe": data.get("sharpe_weekly", data.get("sharpe")),
                "modified": datetime.fromtimestamp(
                    os.path.getmtime(path)).isoformat(timespec="minutes"),
            })
        except Exception:
            continue

    # Live/in-progress logs
    for path in glob.glob(os.path.join(ENGINE_DIR, "*backtest*log.txt")):
        name = os.path.basename(path)
        if "dynuniverse" in name:
            running = is_backtest_running("adaptive_backtest_v3_dynuniverse.py")
        elif "v3" in name:
            running = is_backtest_running("adaptive_backtest_v3.py")
        elif "v2" in name:
            running = is_backtest_running("adaptive_backtest_v2.py")
        else:
            running = False
        results.append({
            "name": name,
            "type": "running" if running else "log",
            "path": path,
            "modified": datetime.fromtimestamp(
                os.path.getmtime(path)).isoformat(timespec="minutes"),
        })

    return results


def save_backtest_snapshot(log_filename, save_name):
    """
    Save the current state of a live log as a permanent named
    snapshot -- lets the user preserve a specific run's results
    (e.g. "v2_run_aug6") even if the log file itself later gets
    overwritten by a future run using the same filename.
    """
    records = parse_live_log(log_filename, max_points=999999)
    if not records:
        return None

    snapshot = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "source_log": log_filename,
        "record_count": len(records),
        "records": records,
    }

    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', save_name)
    out_path = os.path.join(DATA_DIR, f"snapshot_{safe_name}.json")
    with open(out_path, 'w') as f:
        json.dump(snapshot, f)
    return out_path


if __name__ == "__main__":
    print("Available backtests:")
    for bt in list_available_backtests():
        print(f"  {bt}")
    print()
    print("Parsing current v2 log (last 5 rows):")
    records = parse_live_log("adaptive_backtest_v3_log.txt")
    for r in records[-5:]:
        print(f"  {r}")
    print(f"\nTotal parsed: {len(records)}")
    print(f"Currently running: {is_backtest_running()}")
