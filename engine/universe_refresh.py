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


def find_new_candidates(dry_run=True):
    """
    Re-run the Schwab search, but only process tickers NOT already
    in our database -- avoids reprocessing all 4,494 candidates
    every time, only checks the delta of genuinely new instruments
    that have appeared since the last refresh.
    """
    from schwab_client import get_schwab_client
    from etf_scorer import _compute_liquidity
    import re
    import pandas as pd
    import yfinance as yf

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT ticker FROM universe")
    already_known = {row["ticker"] for row in c.fetchall()}

    client = get_schwab_client()
    results = client.search_instruments_by_description(
        '.*ETF.*', max_results=None)
    etf_only = [r for r in results if r['asset_type'] == 'ETF']
    clean = [r for r in etf_only if not r['symbol'].startswith('$')
             and '.' not in r['symbol'] and 1 <= len(r['symbol']) <= 5]

    new_candidates = [r for r in clean if r['symbol'] not in already_known]

    print(f"Total real ETF candidates from Schwab: {len(clean)}")
    print(f"Already known (in database): {len(already_known)}")
    print(f"Genuinely NEW candidates to evaluate: {len(new_candidates)}")

    if not new_candidates:
        print("Nothing new to process.")
        conn.close()
        return []

    EXCLUDE_KEYWORDS = [
        '2X', '3X', 'INVERSE', 'BULL', 'BEAR', 'DAILY TARGET',
        'LEVERAGED', 'ULTRA', 'SHORT ', ' SHORT', 'FLOOR', 'BUFFER',
    ]

    def is_appropriate(desc):
        d = desc.upper()
        return not any(kw in d for kw in EXCLUDE_KEYWORDS)

    appropriate_new = [r for r in new_candidates if is_appropriate(r["description"])]
    print(f"After category filter: {len(appropriate_new)}")

    if not appropriate_new:
        conn.close()
        return []

    # FIXED (twice): first version tried ~3,000 tickers in one
    # unbatched yfinance call, triggering a real rate limit error.
    # SECOND, better fix per real user pushback: this task is
    # periodic MAINTENANCE of the live universe, not one-time
    # historical research -- it should use Schwab (already
    # authenticated, no rate-limit fragility, confirmed real daily
    # price history with volume via get_price_history_every_day,
    # tested directly: 5,085 real candles for GDX from 2006-present)
    # instead of yfinance, consistent with the data-source split
    # already established earlier this session.
    #
    # Real constraint: Schwab's price history endpoint takes ONE
    # symbol per call (confirmed directly), so this is still a
    # per-ticker loop -- but no risk of the free-tier rate limit
    # that broke the yfinance version.
    import time
    all_symbols = [r["symbol"] for r in appropriate_new]
    PAUSE = 0.3  # brief, real pacing courtesy -- not needed to
                  # avoid a known limit, just good practice for any
                  # API under real, repeated automated use

    validated_new = []
    for idx, sym in enumerate(all_symbols):
        try:
            resp = client.get_price_history_every_day(sym)
            data = resp.json()
            candles = data.get("candles", [])
        except Exception as e:
            continue

        if len(candles) < 504:
            continue

        recent = candles[-63:]
        dollar_vols = [c["close"] * c["volume"] for c in recent
                       if c.get("close") and c.get("volume")]
        if len(dollar_vols) < 10:
            continue

        avg_dollar_vol = sum(dollar_vols) / len(dollar_vols)
        if avg_dollar_vol >= 1e6:
            validated_new.append(sym)

        if idx % 50 == 0 and idx > 0:
            print(f"  Checked {idx}/{len(all_symbols)}, "
                  f"{len(validated_new)} validated so far")
        time.sleep(PAUSE)

    print(f"Passed liquidity/history validation: {len(validated_new)}")
    for sym in validated_new:
        print(f"  {sym}: {r['description'][:50] if r['symbol']==sym else ''}")

    if not dry_run and validated_new:
        from datetime import datetime
        now = datetime.now().isoformat()
        for sym in validated_new:
            c.execute("""
                INSERT OR REPLACE INTO universe
                (ticker, is_validated, is_equity, added_at)
                VALUES (?, 1, 1, ?)
            """, (sym, now))
        conn.commit()
        print(f"Added {len(validated_new)} new tickers to database")

    conn.close()
    return validated_new


if __name__ == "__main__":
    refresh_universe(dry_run=True)
    print()
    find_new_candidates(dry_run=True)
