"""
Curated short backtest windows for fast iteration -- NOT a
replacement for the full 22-year run, but the tool to use FIRST,
before ever committing to a multi-hour full run.

Covers the specific periods that matter most for catching real
problems, based on tonight's actual experience:
  - 2007-2013: full 2008 crisis + the slow 2012 recovery
  - 2019-2023: COVID crash + 2022 rate-driven grind

Each window runs in a fraction of the time of the full backtest
(roughly 6-7 years each vs 22), while still exercising the exact
crisis/calm regime types that caught real bugs tonight.

Use this to validate any change BEFORE running the full 22-year
backtest. Only run the full 22 years once a short window already
looks clean and correct.
"""
import time
from adaptive_backtest_v3 import run_adaptive_v3

WINDOWS = {
    "crisis_and_recovery": {
        "start": "2007-01-05",
        "end": "2013-12-31",
        "description": "Full 2008 crisis (Lehman, the crash, the "
                       "bottom) + the slow 2012 European-crisis "
                       "recovery period. Catches: crisis-side "
                       "correctness, dial lag/escalation behavior, "
                       "whether calm-period recovery holds up "
                       "after a real crash. ~7 years.",
    },
    "covid_and_2022": {
        "start": "2019-06-28",
        "end": "2023-06-30",
        "description": "COVID crash (fastest crash in the dataset) "
                       "+ the slow 2022 rate-driven grind. Catches: "
                       "fast-shock response, TBF/short behavior in "
                       "a rate crisis, different crisis SHAPE than "
                       "2008 (grinding vs sudden). ~4 years.",
    },
}


def run_window(name, verbose=True):
    if name not in WINDOWS:
        raise ValueError(f"Unknown window: {name}. "
                         f"Options: {list(WINDOWS.keys())}")

    w = WINDOWS[name]
    print(f"=== Running window: {name} ===")
    print(f"    {w['description']}")
    print(f"    Start: {w['start']}")

    t0 = time.time()
    result = run_adaptive_v3(start=w["start"], end=w["end"], verbose=verbose)
    elapsed = time.time() - t0
    print(f"\n[Window '{name}' complete in {elapsed/60:.1f} minutes]")
    return result


# NOTE for future runs: when launching a window test to a log file
# from the command line, name the output file with "backtest" in
# it (e.g. "window_backtest_crisis_recovery_log.txt") so
# backtest_reader.py's glob pattern (*backtest*log.txt) picks it
# up automatically for the Live Runs dashboard tab. This run's log
# (window_crisis_recovery_log.txt) does NOT match and will not
# appear in the picker -- confirmed harmless, just not visible in
# the dashboard picker list. Use tail -f directly to watch it.


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] in WINDOWS:
        run_window(sys.argv[1])
    else:
        print("Usage: python3 backtest_windows.py <window_name>")
        print(f"Available windows: {list(WINDOWS.keys())}")
        for name, w in WINDOWS.items():
            print(f"\n{name}:")
            print(f"  {w['description']}")
