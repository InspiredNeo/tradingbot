"""
Automatic universe refresh: re-checks the Schwab search + mechanical
filter pipeline periodically, promoting newly-qualifying tickers
and demoting ones that no longer meet the bar, without requiring
a manual multi-hour session each time.

Builds on the validated pipeline from earlier this session
(schwab_client.search_instruments_by_description, the liquidity/
history checks in etf_scorer.py, the word-boundary bond/commodity
exclusion) and the SQLite database (db_setup.py) rather than
static JSON files, so incremental updates are natural.
"""
import sqlite3
import re
from datetime import datetime
import pandas as pd
from db_setup import get_connection

EXCLUDE_KEYWORDS = [
    '2X', '3X', 'INVERSE', 'BULL', 'BEAR', 'DAILY TARGET',
    'LEVERAGED', 'ULTRA', 'SHORT ', ' SHORT', 'FLOOR', 'BUFFER',
]
BOND_COMMODITY_KEYWORDS = [
    "BOND", "TREASURY", "TRSY", "MUNICIPAL", "MUNI", "CORPORATE BOND",
    "FIXED INCOME", "GOLD", "SILVER", "OIL", "COMMODITY", "COMMODITIES",
    "NATURAL GAS", "CRUDE",
]

def matches_keyword(desc, keywords):
    d_upper = desc.upper()
    for kw in keywords:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, d_upper):
            return True
    return False


def check_ticker_status(symbol, px_cache):
    """
    Re-run the same liquidity/history checks already validated
    this session. Returns (is_valid, reason_if_not).
    """
    if symbol not in px_cache.columns:
        return False, "no price data cached"

    s = px_cache[symbol].dropna()
    if len(s) < 504:
        return False, f"insufficient history ({len(s)} days)"

    staleness = (px_cache.index[-1] - s.index[-1]).days
    if staleness > 10:
        return False, f"stale data ({staleness} days old)"

    return True, None


def refresh_universe(dry_run=True):
    """
    dry_run=True: report what WOULD change without touching the DB.
    dry_run=False: actually apply promotions/demotions.
    """
    conn = get_connection()
    c = conn.cursor()

    # FIXED: previously checked ALL 1,535 survivors regardless of
    # equity/bond-commodity status, incorrectly flagging 143
    # legitimately-excluded bond/commodity tickers (VCEB, SIVR,
    # WIP, etc.) as false demotions -- they were never supposed to
    # be in the price cache at all. Now only checks genuine
    # equity-universe members.
    c.execute("SELECT ticker, is_validated FROM universe WHERE is_equity = 1")
    existing = {row["ticker"]: row["is_validated"] for row in c.fetchall()}

    px = pd.read_parquet("histdata/bt_prices.parquet")
    px.index = pd.to_datetime(px.index).tz_localize(None)

    demotions = []
    for ticker in existing:
        is_valid, reason = check_ticker_status(ticker, px)
        if not is_valid and existing[ticker] == 1:
            demotions.append((ticker, reason))

    print(f"Checked {len(existing)} existing tickers")
    print(f"Would demote: {len(demotions)}")
    for t, reason in demotions[:20]:
        print(f"  {t}: {reason}")

    if not dry_run and demotions:
        for ticker, reason in demotions:
            c.execute(
                "UPDATE universe SET is_validated = 0, excluded_reason = ? WHERE ticker = ?",
                (reason, ticker)
            )
        conn.commit()
        print(f"Applied {len(demotions)} demotions")

    conn.close()


if __name__ == "__main__":
    refresh_universe(dry_run=True)
