"""
Live allocation detail -- what the bot would hold RIGHT NOW,
computed instantly from the market-implied dial (no SVI, no lag),
plus a plain-language breakdown of WHY.

Separate from the backtest engine entirely. Safe to import and
call from the dashboard without touching adaptive_backtest_v2.py
or any running process.
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")


def _percentile_rank(value, series):
    if len(series) < 10:
        return 0.5
    return float((series < value).mean())


def compute_dial_with_components(px, date, lookback=504):
    """
    Standalone reimplementation of the component breakdown, kept
    separate from adaptive_backtest_v2.py so this file never has
    to touch the backtest engine while it may still be running.
    Same math, same weights, same signals -- just also returns
    the individual scores instead of only the blend.
    """
    def safe(ticker):
        if ticker not in px.columns:
            return None
        s = px.loc[:date, ticker].dropna()
        return s if len(s) >= 60 else None

    spy  = safe("SPY");  hyg  = safe("HYG");  lqd = safe("LQD")
    tlt  = safe("TLT");  shy  = safe("SHY");  gld = safe("GLD")
    eem  = safe("EEM");  schf = safe("SCHF"); vti = safe("VTI")
    agg  = safe("AGG");  vix  = safe("^VIX")

    scores = {}

    # Credit
    if hyg is not None and len(hyg) >= 120:
        hyg_hist = hyg.iloc[-lookback:] if len(hyg) >= lookback else hyg
        lev = 1.0 - _percentile_rank(hyg.iloc[-1], hyg_hist)
        if lqd is not None and len(lqd) >= 120:
            hyg_win = hyg.iloc[-lookback:] if len(hyg) >= lookback else hyg
            lqd_win = lqd.iloc[-lookback:] if len(lqd) >= lookback else lqd
            h = hyg_win / hyg_win.iloc[0] * 100
            l = lqd_win / lqd_win.iloc[0] * 100
            spread = (h - l).dropna()
            spread_s = 1.0 - _percentile_rank(spread.iloc[-1], spread)
            scores["credit"] = float(0.70 * lev + 0.30 * spread_s)
        else:
            scores["credit"] = float(lev)
    elif agg is not None and len(agg) >= 120:
        agg_hist = agg.iloc[-lookback:] if len(agg) >= lookback else agg
        scores["credit"] = float(1.0 - _percentile_rank(agg.iloc[-1], agg_hist))

    # Volatility (VIX primary)
    if vix is not None and len(vix) >= 126:
        vix_hist = vix.iloc[-lookback:] if len(vix) >= lookback else vix
        vix_now = float(vix.iloc[-1])
        pct = _percentile_rank(vix_now, vix_hist)
        absl = float(np.clip((vix_now - 12) / 28, 0, 1))
        scores["vol"] = float(0.70 * pct + 0.30 * absl)
    elif spy is not None and len(spy) >= 126:
        rets = spy.pct_change().dropna()
        cv = float(rets.iloc[-21:].std() * np.sqrt(252))
        hv = (rets.rolling(21).std().dropna() * np.sqrt(252))
        hv = hv.iloc[-lookback:] if len(hv) >= lookback else hv
        pct = _percentile_rank(cv, hv)
        absl = float(np.clip((cv - 0.12) / 0.20, 0, 1))
        scores["vol"] = float(0.65 * pct + 0.35 * absl)

    # Rate stress x credit interaction
    if tlt is not None and shy is not None and len(tlt) >= 120:
        ratio = (tlt / shy).dropna()
        hist = ratio.iloc[-lookback:] if len(ratio) >= lookback else ratio
        rate_pct = 1.0 - _percentile_rank(ratio.iloc[-1], hist)
        credit_score = scores.get("credit", 0.40)
        weight = 0.40 + 0.60 * credit_score
        scores["rate"] = float(np.clip(rate_pct * weight, 0, 1))

    # International risk appetite
    if eem is not None and schf is not None and len(eem) >= 120:
        er = eem.pct_change(63).dropna(); scr = schf.pct_change(63).dropna()
        common = er.index.intersection(scr.index)
        if len(common) >= 40:
            spread = (scr.loc[common] - er.loc[common]).dropna()
            hist = spread.iloc[-lookback:] if len(spread) >= lookback else spread
            scores["intl"] = float(np.clip(_percentile_rank(spread.iloc[-1], hist), 0, 1))
    elif spy is not None and vti is not None and len(vti) >= 120:
        sr = spy.pct_change(63).dropna(); vr = vti.pct_change(63).dropna()
        common = sr.index.intersection(vr.index)
        if len(common) >= 40:
            spread = (sr.loc[common] - vr.loc[common]).dropna()
            hist = spread.iloc[-lookback:] if len(spread) >= lookback else spread
            scores["intl"] = float(np.clip(_percentile_rank(spread.iloc[-1], hist), 0, 1))

    # Gold flight-to-safety
    if gld is not None and spy is not None and len(gld) >= 126:
        gr = gld.pct_change(126).dropna(); sr = spy.pct_change(126).dropna()
        common = gr.index.intersection(sr.index)
        if len(common) >= 40:
            outperf = (gr.loc[common] - sr.loc[common]).dropna()
            hist = outperf.iloc[-lookback:] if len(outperf) >= lookback else outperf
            scores["gold"] = float(np.clip(_percentile_rank(outperf.iloc[-1], hist), 0, 1))
    elif tlt is not None and spy is not None and len(tlt) >= 126:
        tr = tlt.pct_change(126).dropna(); sr = spy.pct_change(126).dropna()
        common = tr.index.intersection(sr.index)
        if len(common) >= 40:
            outperf = (tr.loc[common] - sr.loc[common]).dropna()
            hist = outperf.iloc[-lookback:] if len(outperf) >= lookback else outperf
            scores["gold"] = float(np.clip(_percentile_rank(outperf.iloc[-1], hist), 0, 1))

    weights = {"credit": 0.35, "vol": 0.30, "rate": 0.18, "intl": 0.10, "gold": 0.07}
    total_w, dial = 0.0, 0.0
    for k, w in weights.items():
        if k in scores:
            dial += scores[k] * w
            total_w += w
    dial = float(np.clip(dial / total_w, 0, 1)) if total_w > 0 else 0.40

    return dial, scores, weights


LABELS = {
    "credit": "Credit markets",
    "vol":    "Volatility",
    "rate":   "Rate stress",
    "intl":   "Global risk appetite",
    "gold":   "Flight-to-safety demand",
}


def _severity_word(score):
    """
    Generic severity word from a 0-1 score. Only used as a fallback
    when a component-specific description isn't available -- each
    component is already its own percentile rank against its own
    history, so a shared 5-tier label doesn't misfire the way a
    shared raw-value threshold would.
    """
    return ("very calm"       if score < 0.20 else
            "calm"            if score < 0.35 else
            "mildly elevated" if score < 0.50 else
            "elevated"        if score < 0.65 else
            "stressed"        if score < 0.80 else
            "severely elevated")


def _explain_component(name, score, dial):
    """
    Plain-language read of one component, described relative to
    the overall dial rather than in isolation -- so a component
    that agrees with a calm overall reading isn't described with
    alarming language just because its own percentile is high.
    """
    label = LABELS.get(name, name)
    agrees_with_calm = dial < 0.35 and score < 0.50
    agrees_with_stress = dial >= 0.50 and score >= 0.50
    disagrees = not (agrees_with_calm or agrees_with_stress)

    word = _severity_word(score)

    if disagrees:
        direction = "higher" if score > dial else "lower"
        return (f"{label} is reading {direction} than the overall "
                f"picture ({score:.2f} vs blended {dial:.2f}) -- "
                f"an outlier, not the main driver")
    else:
        return f"{label} confirms the overall reading ({word}, {score:.2f})"


def get_live_allocation():
    """
    Returns current target allocation PLUS a plain-language
    breakdown of which components are driving the dial reading.
    """
    sys.path.insert(0, os.path.expanduser("~/tradingbot/engine"))
    from adaptive_backtest_v2 import continuous_allocation, get_scenario_label

    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)
    today = px.index[-1]

    dial, scores, weights = compute_dial_with_components(px, today)
    alloc = continuous_allocation(dial)
    label = get_scenario_label(dial)

    # Rank components by how much they DISAGREE with the blended
    # dial (|score - dial|), not by raw magnitude. A component that
    # agrees with a calm consensus isn't "driving" anything even if
    # its own raw score is high -- it's confirming, not leading.
    disagreements = sorted(
        ((k, scores[k], abs(scores[k] - dial)) for k in scores if k in weights),
        key=lambda x: -x[2]
    )

    reasoning_lines = [
        _explain_component(name, score, dial) for name, score, w in
        [(n, s, weights.get(n, 0)) for n, s, d in disagreements]
    ]

    biggest_outlier = disagreements[0] if disagreements else None
    TOP_LABELS = {
        "credit": "credit markets", "vol": "volatility",
        "rate": "rate stress", "intl": "global risk appetite",
        "gold": "flight-to-safety demand",
    }

    n_components = len(scores)
    # Use the SAME zone-based agreement definition as
    # _explain_component, not a separate gap threshold -- otherwise
    # the summary count and the per-component lines can disagree
    # with each other, which defeats the purpose of this panel.
    def _agrees(score, dial):
        agrees_with_calm = dial < 0.35 and score < 0.50
        agrees_with_stress = dial >= 0.50 and score >= 0.50
        return agrees_with_calm or agrees_with_stress
    n_agreeing = sum(1 for _, s, d in disagreements if _agrees(s, dial))

    if biggest_outlier and biggest_outlier[2] >= 0.20:
        name, score, gap = biggest_outlier
        direction = "higher" if score > dial else "lower"
        summary = (
            f"{n_agreeing} of {n_components} signals agree with the "
            f"overall {('calm' if dial < 0.5 else 'elevated')} reading. "
            f"{TOP_LABELS.get(name, name).capitalize()} is the outlier, "
            f"reading {direction} than the rest."
        )
    elif n_components > 0:
        summary = (
            f"All {n_components} signals broadly agree -- "
            f"{('calm' if dial < 0.35 else 'moderate' if dial < 0.65 else 'elevated')} "
            f"conditions across the board, no single driver."
        )
    else:
        summary = "Dial computed from limited data -- treat with caution."

    shorts = {k: v for k, v in alloc["shorts"].items() if v > 0.005}

    result = {
        "as_of": str(today.date()),
        "dial": round(dial, 4),
        "scenario_label": label,
        "equity_pct": round(alloc["equity_target"] * 100, 1),
        "defensive_pct": round(alloc["defensive"] * 100, 1),
        "dbmf_pct": round(alloc["dbmf"] * 100, 1),
        "gld_min_pct": round(alloc["gld_min"] * 100, 1),
        "shorts": {k: round(v * 100, 1) for k, v in shorts.items()},
        "leverage": alloc["leverage"],
        "summary": summary,
        "reasoning": reasoning_lines,
        "computed_at": datetime.now().isoformat(timespec="seconds"),
    }
    _append_to_log(result)
    return result


LOG_PATH = os.path.expanduser("~/tradingbot/engine/allocation_log.txt")


def _append_to_log(alloc):
    """
    Append one line to the running allocation log. Plain append-only
    text file -- same pattern as monitor_log.txt elsewhere in this
    project. No state, no database, just a growing history of what
    the bot computed and why, at each moment someone checked.
    """
    shorts_str = ", ".join(f"{k} {v:.1f}%" for k, v in alloc.get("shorts", {}).items())
    shorts_part = f" | shorts: {shorts_str}" if shorts_str else ""

    line = (
        f"{alloc['computed_at']} | as_of {alloc['as_of']} | "
        f"dial={alloc['dial']:.3f} [{alloc['scenario_label']}] | "
        f"eq={alloc['equity_pct']:.1f}% def={alloc['defensive_pct']:.1f}% "
        f"dbmf={alloc['dbmf_pct']:.1f}%{shorts_part} | "
        f"{alloc.get('summary','')}\n"
    )
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass  # logging failure should never break the live panel


def read_allocation_log(n=20):
    """
    Return the last n entries from the allocation log, most recent
    first. Returns empty list if the log doesn't exist yet.
    """
    if not os.path.exists(LOG_PATH):
        return []
    try:
        with open(LOG_PATH) as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
        return list(reversed(lines[-n:]))
    except Exception:
        return []


if __name__ == "__main__":
    import json
    result = get_live_allocation()
    print(json.dumps(result, indent=2))
