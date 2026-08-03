"""
Sentiment Signals for Market Terminal Bot Engine.
6 sentiment signals that capture market participant behavior.

Signals:
1.  AI news sentiment score (from terminal news feed)
2.  Insider trading signal (net buying vs selling)
3.  Options put/call ratio
4.  Short interest aggregate
5.  Analyst revision momentum
6.  Earnings surprise momentum
"""

import os
import time
import numpy as np
import pandas as pd
import yfinance as yf
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
AV_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Cache
_cache = {}
_cache_ts = {}
CACHE_TTL = 3600


def _cached(key, fn, ttl=CACHE_TTL):
    now = time.time()
    if key in _cache and now - _cache_ts.get(key, 0) < ttl:
        return _cache[key]
    result = fn()
    _cache[key] = result
    _cache_ts[key] = now
    return result


# Core ETF/stock universe for sentiment analysis
CORE_SYMBOLS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN",
                "META", "TSLA", "JPM", "SPY", "QQQ"]


# ── Signal functions ───────────────────────────────────────────

def get_news_sentiment():
    """
    Pull AI sentiment scores from the terminal's news cache.
    Falls back to Alpha Vantage if cache unavailable.
    """
    def _fetch():
        # Try to read from terminal's news cache first
        try:
            import sys
            sys.path.append(os.path.expanduser("~/tradingbot/dashboard"))
            from dash_app import _news_cache
            feed = _news_cache.get("feed", [])
            if feed:
                labels = [a.get("overall_sentiment_label", "Neutral")
                          for a in feed]
                bullish = sum(1 for l in labels if "Bullish" in l)
                bearish = sum(1 for l in labels if "Bearish" in l)
                total = len(labels)
                bull_pct = bullish / total if total else 0.5
                bear_pct = bearish / total if total else 0.5
                score = bull_pct - bear_pct  # -1 to +1
                return {
                    "score": score,
                    "bullish_pct": bull_pct,
                    "bearish_pct": bear_pct,
                    "total_articles": total,
                    "source": "terminal_cache",
                    "signal": "bullish" if score > 0.1 else
                              "bearish" if score < -0.1 else "neutral",
                }
        except Exception:
            pass

        # Fall back to Alpha Vantage news sentiment
        try:
            resp = requests.get(
                "https://www.alphavantage.co/query",
                params={"function": "NEWS_SENTIMENT", "apikey": AV_KEY,
                        "limit": 50, "sort": "LATEST"},
                timeout=15,
            )
            feed = resp.json().get("feed", [])
            if feed:
                scores = [float(a.get("overall_sentiment_score", 0))
                          for a in feed]
                avg_score = np.mean(scores) if scores else 0
                bull_pct = sum(1 for s in scores if s > 0.1) / len(scores)
                bear_pct = sum(1 for s in scores if s < -0.1) / len(scores)
                return {
                    "score": avg_score,
                    "bullish_pct": bull_pct,
                    "bearish_pct": bear_pct,
                    "total_articles": len(scores),
                    "source": "alpha_vantage",
                    "signal": "bullish" if avg_score > 0.1 else
                              "bearish" if avg_score < -0.1 else "neutral",
                }
        except Exception:
            pass

        return {"score": 0.0, "bullish_pct": 0.5, "bearish_pct": 0.5,
                "total_articles": 0, "source": "none", "signal": "neutral"}

    return _cached("news_sentiment", _fetch)


def get_insider_signal():
    """
    Aggregate insider buying vs selling across core symbols.
    Net buying = bullish signal. Net selling = bearish.
    Based on research by Seyhun (1986) and Lakonishok & Lee (2001).
    """
    def _fetch():
        total_buys = 0
        total_sells = 0
        total_buy_value = 0
        total_sell_value = 0

        def fetch_one(sym):
            try:
                resp = requests.get(
                    "https://finnhub.io/api/v1/stock/insider-transactions",
                    params={"symbol": sym, "token": FINNHUB_KEY},
                    timeout=10,
                )
                trades = resp.json().get("data", [])
                buys = sells = buy_val = sell_val = 0
                for t in trades[:20]:
                    shares = t.get("change", 0)
                    price = t.get("transactionPrice", 0) or 0
                    value = abs(shares * price)
                    if t.get("transactionCode") in ["B", "P"] and shares > 0:
                        buys += 1
                        buy_val += value
                    elif t.get("transactionCode") == "S" and shares < 0:
                        sells += 1
                        sell_val += value
                return buys, sells, buy_val, sell_val
            except Exception:
                return 0, 0, 0, 0

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(fetch_one, sym) for sym in CORE_SYMBOLS]
            for f in as_completed(futures):
                b, s, bv, sv = f.result()
                total_buys += b
                total_sells += s
                total_buy_value += bv
                total_sell_value += sv

        total_trades = total_buys + total_sells
        buy_ratio = total_buys / total_trades if total_trades else 0.5
        # Value-weighted signal
        total_value = total_buy_value + total_sell_value
        value_ratio = total_buy_value / total_value if total_value else 0.5

        # Combined score: count + value weighted
        score = (buy_ratio * 0.4 + value_ratio * 0.6) * 2 - 1  # -1 to +1

        return {
            "total_buys": total_buys,
            "total_sells": total_sells,
            "buy_ratio": buy_ratio,
            "value_ratio": value_ratio,
            "score": score,
            "signal": "bullish" if score > 0.2 else
                      "bearish" if score < -0.2 else "neutral",
        }

    return _cached("insider", _fetch, ttl=86400)  # cache 24 hours


def get_put_call_ratio():
    """
    Options put/call ratio for SPY and QQQ.
    High PCR (>1.2) = fear/bearish. Low PCR (<0.7) = complacency/bullish.
    Contrarian signal: extreme readings often precede reversals.
    """
    def _fetch():
        ratios = {}
        for sym in ["SPY", "QQQ"]:
            try:
                t = yf.Ticker(sym)
                if not t.options:
                    continue
                # Use nearest expiry
                chain = t.option_chain(t.options[0])
                call_vol = chain.calls["volume"].fillna(0).sum()
                put_vol = chain.puts["volume"].fillna(0).sum()
                if call_vol > 0:
                    ratios[sym] = float(put_vol / call_vol)
            except Exception:
                continue

        if not ratios:
            return {"ratio": 1.0, "signal": "neutral", "contrarian": "neutral"}

        avg_ratio = np.mean(list(ratios.values()))

        # Primary signal (trend following)
        if avg_ratio > 1.2:
            signal = "bearish"
        elif avg_ratio < 0.7:
            signal = "bullish"
        else:
            signal = "neutral"

        # Contrarian signal (extreme readings)
        if avg_ratio > 1.5:
            contrarian = "bullish"  # extreme fear = buy signal
        elif avg_ratio < 0.5:
            contrarian = "bearish"  # extreme complacency = sell signal
        else:
            contrarian = "neutral"

        return {
            "ratios": ratios,
            "avg_ratio": avg_ratio,
            "signal": signal,
            "contrarian": contrarian,
        }

    return _cached("put_call", _fetch, ttl=300)  # 5 min cache (market hours)


def get_short_interest_signal():
    """
    Aggregate short interest across core symbols.
    Rising short interest = bearish sentiment.
    High short interest + price rising = squeeze risk.
    """
    def _fetch():
        short_pcts = []
        changes = []

        def fetch_one(sym):
            try:
                info = yf.Ticker(sym).info
                pct = info.get("shortPercentOfFloat", 0) or 0
                shares_short = info.get("sharesShort", 0) or 0
                shares_prior = info.get("sharesShortPriorMonth", 0) or 0
                change = ((shares_short - shares_prior) / shares_prior
                          if shares_prior else 0)
                return pct, change
            except Exception:
                return 0, 0

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(fetch_one, sym) for sym in CORE_SYMBOLS[:8]]
            for f in as_completed(futures):
                pct, chg = f.result()
                if pct > 0:
                    short_pcts.append(pct)
                    changes.append(chg)

        if not short_pcts:
            return {"avg_short_pct": 0.02, "change": 0, "signal": "neutral"}

        avg_pct = np.mean(short_pcts)
        avg_change = np.mean(changes)

        # Rising short interest = bearish
        signal = "bearish" if avg_change > 0.05 else \
                 "bullish" if avg_change < -0.05 else "neutral"

        return {
            "avg_short_pct": avg_pct,
            "avg_monthly_change": avg_change,
            "signal": signal,
            "squeeze_risk": avg_pct > 0.15 and avg_change < -0.05,
        }

    return _cached("short_interest", _fetch, ttl=86400)  # cache 24 hours


def get_analyst_revision_momentum():
    """
    Are analysts revising earnings estimates up or down?
    Upward revisions = improving fundamentals = bullish.
    """
    def _fetch():
        upgrades = downgrades = 0
        strong_buys = buys = holds = sells = strong_sells = 0

        def fetch_one(sym):
            try:
                resp = requests.get(
                    "https://finnhub.io/api/v1/stock/recommendation",
                    params={"symbol": sym, "token": FINNHUB_KEY},
                    timeout=10,
                )
                data = resp.json()
                if len(data) >= 2:
                    curr = data[0]
                    prev = data[1]
                    # Score: strongBuy=5, buy=4, hold=3, sell=2, strongSell=1
                    def score(d):
                        return (d.get("strongBuy", 0) * 5 +
                                d.get("buy", 0) * 4 +
                                d.get("hold", 0) * 3 +
                                d.get("sell", 0) * 2 +
                                d.get("strongSell", 0) * 1)
                    curr_score = score(curr)
                    prev_score = score(prev)
                    return (1 if curr_score > prev_score else 0,
                            1 if curr_score < prev_score else 0,
                            curr.get("strongBuy", 0),
                            curr.get("buy", 0),
                            curr.get("hold", 0),
                            curr.get("sell", 0),
                            curr.get("strongSell", 0))
                return 0, 0, 0, 0, 0, 0, 0
            except Exception:
                return 0, 0, 0, 0, 0, 0, 0

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(fetch_one, sym) for sym in CORE_SYMBOLS]
            for f in as_completed(futures):
                up, dn, sb, b, h, s, ss = f.result()
                upgrades += up
                downgrades += dn
                strong_buys += sb
                buys += b
                holds += h
                sells += s
                strong_sells += ss

        total_ratings = strong_buys + buys + holds + sells + strong_sells
        if total_ratings == 0:
            return {"revision_score": 0, "signal": "neutral"}

        # Consensus score 1-5
        consensus = ((strong_buys * 5 + buys * 4 + holds * 3 +
                      sells * 2 + strong_sells) / total_ratings)

        revision_score = upgrades - downgrades
        signal = "bullish" if revision_score > 0 else \
                 "bearish" if revision_score < 0 else "neutral"

        return {
            "upgrades": upgrades,
            "downgrades": downgrades,
            "revision_score": revision_score,
            "consensus_score": consensus,
            "signal": signal,
        }

    return _cached("analyst_revision", _fetch, ttl=86400)  # cache 24 hours


def get_earnings_surprise_momentum():
    """
    Recent earnings surprise trend.
    Companies consistently beating estimates = positive momentum.
    """
    def _fetch():
        beats = misses = total = 0
        surprise_pcts = []

        def fetch_one(sym):
            try:
                resp = requests.get(
                    "https://finnhub.io/api/v1/stock/earnings",
                    params={"symbol": sym, "token": FINNHUB_KEY},
                    timeout=10,
                )
                data = resp.json()
                b = m = 0
                surprises = []
                for e in data[:4]:  # last 4 quarters
                    actual = e.get("actual")
                    est = e.get("estimate")
                    if actual is not None and est is not None and est != 0:
                        surprise = (actual - est) / abs(est)
                        surprises.append(surprise)
                        if actual > est:
                            b += 1
                        else:
                            m += 1
                return b, m, surprises
            except Exception:
                return 0, 0, []

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = [ex.submit(fetch_one, sym) for sym in CORE_SYMBOLS]
            for f in as_completed(futures):
                b, m, surprises = f.result()
                beats += b
                misses += m
                total += b + m
                surprise_pcts.extend(surprises)

        beat_rate = beats / total if total else 0.5
        avg_surprise = np.mean(surprise_pcts) if surprise_pcts else 0

        signal = "bullish" if beat_rate > 0.6 and avg_surprise > 0.02 else \
                 "bearish" if beat_rate < 0.4 or avg_surprise < -0.02 else "neutral"

        return {
            "beats": beats,
            "misses": misses,
            "beat_rate": beat_rate,
            "avg_surprise_pct": avg_surprise,
            "signal": signal,
        }

    return _cached("earnings_surprise", _fetch, ttl=86400)  # cache 24 hours


# ── Master collector ───────────────────────────────────────────

def get_all_sentiment_signals(verbose=False):
    """Fetch all 6 sentiment signals in parallel."""
    signal_fns = {
        "news": get_news_sentiment,
        "insider": get_insider_signal,
        "put_call": get_put_call_ratio,
        "short_interest": get_short_interest_signal,
        "analyst_revision": get_analyst_revision_momentum,
        "earnings_surprise": get_earnings_surprise_momentum,
    }

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fn): name
                   for name, fn in signal_fns.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"error": str(e), "signal": "neutral"}

    if verbose:
        _print_signals(results)

    vector = _to_feature_vector(results)
    return results, vector


def _to_feature_vector(signals):
    news = signals.get("news", {})
    insider = signals.get("insider", {})
    pcr = signals.get("put_call", {})
    short = signals.get("short_interest", {})
    revision = signals.get("analyst_revision", {})
    earnings = signals.get("earnings_surprise", {})

    vector = np.array([
        # News sentiment (2)
        np.clip(news.get("score", 0) * 3, -3, 3),
        np.clip(news.get("bullish_pct", 0.5) - 0.5, -0.5, 0.5) * 6,

        # Insider (2)
        np.clip(insider.get("score", 0) * 3, -3, 3),
        np.clip(insider.get("value_ratio", 0.5) - 0.5, -0.5, 0.5) * 6,

        # Put/call (2)
        np.clip((1.0 - pcr.get("avg_ratio", 1.0)) * 3, -3, 3),
        1.0 if pcr.get("contrarian") == "bullish" else
        -1.0 if pcr.get("contrarian") == "bearish" else 0.0,

        # Short interest (2)
        np.clip(-short.get("avg_monthly_change", 0) * 10, -3, 3),
        1.0 if short.get("squeeze_risk") else 0.0,

        # Analyst revision (2)
        np.clip(revision.get("revision_score", 0) * 0.5, -3, 3),
        np.clip(revision.get("consensus_score", 3) - 3, -2, 2),

        # Earnings surprise (2)
        np.clip((earnings.get("beat_rate", 0.5) - 0.5) * 6, -3, 3),
        np.clip(earnings.get("avg_surprise_pct", 0) * 20, -3, 3),
    ], dtype=np.float32)

    return vector  # 12 features


def _print_signals(signals):
    print("\n" + "=" * 50)
    print("SENTIMENT SIGNALS")
    print("=" * 50)

    n = signals.get("news", {})
    print(f"\nNews Sentiment: {n.get('signal', 'N/A').upper()}")
    print(f"  Score: {n.get('score', 0):.3f} | "
          f"Bull: {n.get('bullish_pct', 0)*100:.0f}% | "
          f"Bear: {n.get('bearish_pct', 0)*100:.0f}% | "
          f"Articles: {n.get('total_articles', 0)}")

    i = signals.get("insider", {})
    print(f"\nInsider Trading: {i.get('signal', 'N/A').upper()}")
    print(f"  Buys: {i.get('total_buys', 0)} | "
          f"Sells: {i.get('total_sells', 0)} | "
          f"Buy ratio: {i.get('buy_ratio', 0)*100:.0f}% | "
          f"Score: {i.get('score', 0):.3f}")

    p = signals.get("put_call", {})
    print(f"\nPut/Call Ratio: {p.get('signal', 'N/A').upper()} "
          f"(contrarian: {p.get('contrarian', 'N/A').upper()})")
    print(f"  Avg PCR: {p.get('avg_ratio', 0):.2f} | "
          f"Ratios: {p.get('ratios', {})}")

    s = signals.get("short_interest", {})
    print(f"\nShort Interest: {s.get('signal', 'N/A').upper()}")
    print(f"  Avg short %: {s.get('avg_short_pct', 0)*100:.1f}% | "
          f"Monthly change: {s.get('avg_monthly_change', 0)*100:.1f}% | "
          f"Squeeze risk: {s.get('squeeze_risk', False)}")

    r = signals.get("analyst_revision", {})
    print(f"\nAnalyst Revisions: {r.get('signal', 'N/A').upper()}")
    print(f"  Upgrades: {r.get('upgrades', 0)} | "
          f"Downgrades: {r.get('downgrades', 0)} | "
          f"Consensus: {r.get('consensus_score', 0):.2f}/5")

    e = signals.get("earnings_surprise", {})
    print(f"\nEarnings Surprise: {e.get('signal', 'N/A').upper()}")
    print(f"  Beat rate: {e.get('beat_rate', 0)*100:.0f}% | "
          f"Avg surprise: {e.get('avg_surprise_pct', 0)*100:.1f}%")
    print("=" * 50)


if __name__ == "__main__":
    import time
    print("Fetching sentiment signals...")
    t = time.time()
    signals, vector = get_all_sentiment_signals(verbose=True)
    print(f"\nFetch time: {time.time()-t:.2f}s")
    print(f"Feature vector: {vector.shape} → {vector}")
