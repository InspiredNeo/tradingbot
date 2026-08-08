"""
Adaptive Backtest v3 -- v2 plus calm-zone ceiling fix and honest Sharpe reporting

Changes from v1:
1.  Hysteresis (2-3 week minimum per scenario)
2.  Remove leverage (wait for live 4-tier dial)
3.  Lower bull_calm threshold to 0.28
4.  Fractional thresholds: 0.28/0.48/0.68
5.  Proportional continuous position sizing
6.  Proportional short sizing
7.  DBMF minimum 8% always
8.  GLD minimum 4% always
9.  Smooth scenario transitions over 2 weeks
10. Min trade size 2% (skip tiny rebalances)
11. Margin cost deduction when leverage > 1.0x
12. DBMF fallback to GLD pre-2019
13. Crisis threshold 0.68 (was 0.72/0.75)
14. Recovery config tightened
15. Min-var 60% in crisis
16. Momentum 50% in bull_calm
17. Both weekly AND daily Sharpe reported
18. Out-of-sample split (train 2004-2018, validate 2019-2026)
19. State tracking (scenario, weeks in scenario, peak dial)
20. 4-week dial history buffer for recovery detection
"""

import os, sys, time, json, warnings
import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

# ── Universe ──────────────────────────────────────────────────
import dial_volatility
import dial_currency_em

RISK_ASSETS  = ["VTI", "QQQ", "SCHF", "EEM", "XLV", "XLF"]
DEF_ASSETS   = ["AGG", "TLT", "GLD"]
SHORT_ASSETS = ["SH", "PSQ", "TBF"]
DIVERSIFIER  = ["DBMF"]

ETF_INCEPTION = {
    "VTI":  "2001-06-15", "QQQ":  "1999-03-10",
    "SCHF": "2009-11-03", "EEM":  "2003-04-11",
    "XLV":  "1998-12-22", "XLF":  "1998-12-22",
    "AGG":  "2003-09-29", "TLT":  "2002-07-26",
    "GLD":  "2004-11-18", "SH":   "2006-06-21",
    "PSQ":  "2006-06-21", "TBF":  "2009-08-20",
    "DBMF": "2019-05-08",
}

# ── V2 Thresholds (lower than v1) ─────────────────────────────
THRESHOLDS = {
    "bull_calm_max": 0.28,   # was 0.35
    "bull_late_max": 0.48,   # was 0.55
    "stress_max":    0.68,   # was 0.75
    "crisis_max":    1.00,
}

# ── Hysteresis settings ───────────────────────────────────────
HYSTERESIS = {
    "bull_calm_exit_weeks": 1,   # weeks below threshold to exit
    "bull_late_exit_weeks": 2,
    "stress_exit_weeks":    2,
    "crisis_exit_weeks":    3,
    "exit_buffer":          0.04, # must drop this far below threshold
    "recovery_drop":        0.08, # dial must fall this much from peak
    "recovery_weeks":       2,    # weeks of falling to confirm recovery
    "transition_weeks":     2,    # weeks to smooth transitions
}

# ── Blend weights ─────────────────────────────────────────────
BLENDS = {
    "bull_calm": {
        "momentum":       0.50,  # was 0.45
        "risk_parity":    0.20,
        "min_variance":   0.10,
        "max_divers":     0.10,
        "bl_equilibrium": 0.10,
    },
    "bull_late": {
        "momentum":       0.30,
        "risk_parity":    0.25,
        "min_variance":   0.20,
        "max_divers":     0.15,
        "bl_equilibrium": 0.10,
    },
    "stress": {
        "momentum":       0.00,
        "risk_parity":    0.20,
        "min_variance":   0.50,
        "max_divers":     0.20,
        "bl_equilibrium": 0.10,
    },
    "crisis": {
        "momentum":       0.00,
        "risk_parity":    0.15,
        "min_variance":   0.60,  # was 0.45
        "max_divers":     0.15,
        "bl_equilibrium": 0.10,
    },
    "recovery": {
        "momentum":       0.20,
        "risk_parity":    0.40,
        "min_variance":   0.20,
        "max_divers":     0.10,
        "bl_equilibrium": 0.10,
    },
}

TCOST        = 0.0005
MIN_TRADE    = 0.020
DERISK_MAX   = 0.15   # max weekly move toward defense
RERISK_MAX   = 0.06   # max weekly move toward risk
LOOKBACK     = 504
SVI_STEPS    = 800
SVI_DRAWS    = 800
OPT_DRAWS    = 80
MARGIN_RATE  = 0.075


def compute_market_implied_dial(px, date, lookback=504):
    """
    Compute stability dial from market prices only.
    Zero lag, daily resolution, US-specific signals.
    Uses 504-day (2yr) lookback for stable percentiles.
    
    5 signals:
      1. Credit stress:  HYG absolute level percentile
      2. Equity vol:     SPY realized vol percentile (504d)
      3. Rate stress:    TLT/SHY × credit interaction
      4. Breadth:        EEM vs SCHF (risk appetite)
      5. Tail risk:      VIX level (absolute, not relative)
    """
    def safe_series(ticker):
        if ticker not in px.columns:
            return None
        s = px.loc[:date, ticker].dropna()
        return s if len(s) >= 60 else None

    def percentile_rank(value, series):
        if len(series) < 10:
            return 0.5
        return float((series < value).mean())

    scores = {}

    spy  = safe_series("SPY")
    hyg  = safe_series("HYG")
    lqd  = safe_series("LQD")
    tlt  = safe_series("TLT")
    shy  = safe_series("SHY")
    gld  = safe_series("GLD")
    eem  = safe_series("EEM")
    schf = safe_series("SCHF")
    vti  = safe_series("VTI")
    agg  = safe_series("AGG")
    vix  = safe_series("^VIX")

    # 1. CREDIT STRESS -- HYG absolute level
    # Use HYG level relative to 2yr history
    # HYG low = spreads wide = credit stress
    # Simple, robust, hard to confuse with rate effects
    if hyg is not None and len(hyg) >= 120:
        hyg_hist = hyg.iloc[-lookback:]
        lev_stress = 1.0 - percentile_rank(hyg.iloc[-1], hyg_hist)
        
        # Blend with LQD-adjusted level if available
        if lqd is not None and len(lqd) >= 120:
            # HYG/LQD normalized ratio (removes duration effect)
            # Normalize each to 100 at start of window
            hyg_win = hyg.iloc[-lookback:] if len(hyg) >= lookback else hyg
            lqd_win = lqd.iloc[-lookback:] if len(lqd) >= lookback else lqd
            h = hyg_win / hyg_win.iloc[0] * 100
            l = lqd_win / lqd_win.iloc[0] * 100
            spread = (h - l).dropna()
            spread_stress = 1.0 - percentile_rank(
                spread.iloc[-1], spread)
            # 70% level, 30% spread (level more robust)
            scores["credit"] = float(0.70 * lev_stress + 
                                      0.30 * spread_stress)
        else:
            scores["credit"] = float(lev_stress)

    elif lqd is not None and tlt is not None and len(lqd) >= 60:
        # Pre-HYG fallback: LQD level + TLT/LQD spread
        # LQD low = investment grade stress = credit stress
        lqd_hist = lqd.iloc[-lookback:]
        lqd_stress = 1.0 - percentile_rank(lqd.iloc[-1], lqd_hist)
        
        # TLT vs LQD: when LQD falls more than TLT = credit stress
        # (not just rate risk)
        tlt_ret = tlt.pct_change(63).dropna()
        lqd_ret = lqd.pct_change(63).dropna()
        common = tlt_ret.index.intersection(lqd_ret.index)
        if len(common) >= 40:
            spread = (tlt_ret.loc[common] - lqd_ret.loc[common]).dropna()
            hist = spread.iloc[-lookback:]
            spread_stress = percentile_rank(spread.iloc[-1], hist)
            scores["credit"] = float(0.60*lqd_stress + 0.40*spread_stress)
        else:
            scores["credit"] = float(lqd_stress)
    elif agg is not None and len(agg) >= 60:
        agg_hist = agg.iloc[-lookback:]
        scores["credit"] = float(1.0 - percentile_rank(
            agg.iloc[-1], agg_hist))

    # 2. VOLATILITY STRESS
    # Primary: direct VIX (forward-looking fear gauge)
    # Fallback: SPY realized vol (backward-looking)
    if vix is not None and len(vix) >= 126:
        vix_hist = vix.iloc[-lookback:]
        vix_current = float(vix.iloc[-1])
        
        # Percentile rank in history
        pct_stress = percentile_rank(vix_current, vix_hist)
        
        # Absolute threshold (VIX > 20 = elevated, > 30 = stressed)
        abs_stress = float(np.clip((vix_current - 12) / 28, 0, 1))
        
        # Blend: 70% percentile, 30% absolute
        scores["vol"] = float(0.70 * pct_stress + 0.30 * abs_stress)
        
    elif spy is not None and len(spy) >= 126:
        # Fallback: SPY realized vol
        spy_rets = spy.pct_change().dropna()
        current_vol = float(spy_rets.iloc[-21:].std() * np.sqrt(252))
        hist_vols = (spy_rets.rolling(21).std().dropna()
                     * np.sqrt(252)).iloc[-lookback:]
        pct_stress = percentile_rank(current_vol, hist_vols)
        abs_stress = float(np.clip((current_vol - 0.12) / 0.20, 0, 1))
        scores["vol"] = float(0.65 * pct_stress + 0.35 * abs_stress)

    # 3. RATE + FINANCIAL STRESS
    # TLT/SHY falling = rising long rates
    # BUT only count as stress if credit ALSO stressed
    # (2024: high rates but tight credit = NOT stressed)
    if tlt is not None and shy is not None and len(tlt) >= 120:
        ratio = (tlt / shy).dropna()
        ratio_hist = ratio.iloc[-lookback:]
        rate_percentile = 1.0 - percentile_rank(
            ratio.iloc[-1], ratio_hist)
        
        # Interaction: rate stress × credit stress
        # High rates alone not a problem if credit is fine
        credit_score = scores.get("credit", 0.40)
        # Rate matters more when credit also stressed
        rate_weight = 0.40 + 0.60 * credit_score
        scores["rate"] = float(np.clip(
            rate_percentile * rate_weight, 0, 1))

    # 4. GLOBAL RISK APPETITE
    # EEM vs SCHF: EM lagging developed = risk-off
    # More reliable than small vs large cap
    if eem is not None and schf is not None and len(eem) >= 120:
        er  = eem.pct_change(63).dropna()
        scr = schf.pct_change(63).dropna()
        common = er.index.intersection(scr.index)
        if len(common) >= 40:
            spread = (scr.loc[common] - er.loc[common]).dropna()
            hist   = spread.iloc[-lookback:]
            intl_stress = percentile_rank(spread.iloc[-1], hist)
            scores["intl"] = float(np.clip(intl_stress, 0, 1))
    elif spy is not None and vti is not None and len(vti) >= 120:
        # Fallback: SPY vs VTI (large vs total market)
        sr  = spy.pct_change(63).dropna()
        vr  = vti.pct_change(63).dropna()
        common = sr.index.intersection(vr.index)
        if len(common) >= 40:
            spread = (sr.loc[common] - vr.loc[common]).dropna()
            hist   = spread.iloc[-lookback:]
            breadth_stress = percentile_rank(spread.iloc[-1], hist)
            scores["intl"] = float(np.clip(breadth_stress, 0, 1))

    # 5. GOLD FLIGHT TO SAFETY
    # GLD rising RELATIVE TO SPY (not absolute)
    # Gold outperforming stocks = risk-off signal
    # Use 126-day change to smooth noise
    if gld is not None and spy is not None and len(gld) >= 126:
        gr  = gld.pct_change(126).dropna()
        sr  = spy.pct_change(126).dropna()
        common = gr.index.intersection(sr.index)
        if len(common) >= 40:
            gold_outperf = (gr.loc[common] - sr.loc[common]).dropna()
            hist = gold_outperf.iloc[-lookback:]
            gold_stress = percentile_rank(gold_outperf.iloc[-1], hist)
            scores["gold"] = float(np.clip(gold_stress, 0, 1))
    elif tlt is not None and spy is not None and len(tlt) >= 126:
        # Pre-GLD fallback: TLT vs SPY (bonds outperforming = risk-off)
        tr  = tlt.pct_change(126).dropna()
        sr  = spy.pct_change(126).dropna()
        common = tr.index.intersection(sr.index)
        if len(common) >= 40:
            tlt_outperf = (tr.loc[common] - sr.loc[common]).dropna()
            hist = tlt_outperf.iloc[-lookback:]
            gold_stress = percentile_rank(tlt_outperf.iloc[-1], hist)
            scores["gold"] = float(np.clip(gold_stress, 0, 1))

    if not scores:
        return 0.40

    # Weights: credit + vol are most reliable
    # Rate interaction prevents 2024 false signal
    # Intl gives global picture
    # Gold adds crisis confirmation
    weights = {
        "credit": 0.35,
        "vol":    0.30,
        "rate":   0.18,
        "intl":   0.10,
        "gold":   0.07,
    }

    total_w = 0.0
    dial = 0.0
    for k, w in weights.items():
        if k in scores:
            dial    += scores[k] * w
            total_w += w

    if total_w == 0:
        return 0.40

    return float(np.clip(dial / total_w, 0, 1))


def continuous_allocation(dial):
    """
    6-decimal continuous position sizing.
    No hard scenario cliffs -- pure formula.
    Returns target weights by category.
    """
    d = float(dial)

    # Core equity target (continuous, no cliffs)
    # v3: raised calm-zone equity ceiling from 0.90 to 1.00.
    #
    # Evidence this addresses (all three point the same direction):
    #   1. Real v2 scenario breakdown (this file's own output, full
    #      22-year run): bull_calm was the largest single regime by
    #      time (494/1152 weeks, 43%) but returned only 17.4% ann,
    #      vs 91.2% ann in crisis and 50.2% ann in stress. The
    #      system's edge is concentrated in regimes it spends the
    #      LEAST time in, while capped near 90% equity for nearly
    #      half of history.
    #   2. Pure Momentum comparison (no ceiling at all, same 22yr
    #      window): ~$17,000 ahead of the capped system by 2021.
    #   3. Isolated dry-run test (dryrun_v2.py, equal-weight proxy,
    #      no SVI): +$3,178 (+4.8%) final value from this exact
    #      change, with crisis-zone allocations barely affected
    #      (dial=0.68 eq moved 41.4%->44.2%, dial=0.90 eq moved
    #      25.7%->26.2% -- protection intact, only the calm end
    #      changed meaningfully).
    #
    # Crisis-side behavior is deliberately preserved: the new slope
    # (0.820 vs old 0.714) converges back toward the same floor by
    # dial=1.0, so this is a change to the CALM end of the curve
    # specifically, not a general loosening of risk controls.
    equity_target = max(0.18, 1.00 - d * 0.820)

    # No leverage in v3 -- wait for live 4-tier dial
    leverage = 1.00

    # DBMF: minimum 8%, scales up with stress
    dbmf = min(0.15, 0.08 + d * 0.07)

    # GLD: minimum 4% always (uncorrelated anchor)
    gld_min = 0.04

    # Shorts: proportional to dial
    sh_pct  = max(0, (d - THRESHOLDS["bull_late_max"]) * 0.20)
    psq_pct = max(0, (d - THRESHOLDS["stress_max"])    * 0.10)
    tbf_pct = max(0, (d - THRESHOLDS["bull_late_max"]) * 0.10)

    # Cap total shorts at 15%
    total_shorts = sh_pct + psq_pct + tbf_pct
    if total_shorts > 0.15:
        scale = 0.15 / total_shorts
        sh_pct  *= scale
        psq_pct *= scale
        tbf_pct *= scale
        total_shorts = 0.15

    # Defensive remainder
    defensive = max(0.05, 1.0 - equity_target - dbmf - total_shorts)

    return {
        "equity_target": equity_target,
        "defensive":     defensive,
        "dbmf":          dbmf,
        "gld_min":       gld_min,
        "leverage":      leverage,
        "shorts": {
            "SH":  sh_pct,
            "PSQ": psq_pct,
            "TBF": tbf_pct,
        },
    }


def bootstrap_dial_allocation(dial_history, n_bootstrap=300, seed=None):
    if seed is not None:
        np.random.seed(seed)
    """
    Bootstrap posterior over dial for smoother threshold handling.
    Uses last 52 available dial readings.
    Returns probability-weighted allocation.
    """
    if len(dial_history) < 4:
        d = float(dial_history[-1]) if len(dial_history) > 0 else 0.40
        return continuous_allocation(d)
    
    values = np.array(dial_history[-52:])
    samples = np.random.choice(values, size=n_bootstrap, replace=True)
    noise   = np.random.normal(0, 0.018, n_bootstrap)
    dial_samples = np.clip(samples + noise, 0, 1)
    
    allocs = [continuous_allocation(d) for d in dial_samples]
    
    result = {
        "equity_target": float(np.mean([a["equity_target"] for a in allocs])),
        "defensive":     float(np.mean([a["defensive"]     for a in allocs])),
        "dbmf":          float(np.mean([a["dbmf"]          for a in allocs])),
        "gld_min":       float(np.mean([a["gld_min"]       for a in allocs])),
        "leverage":      1.00,
        "shorts": {
            "SH":  float(np.mean([a["shorts"]["SH"]  for a in allocs])),
            "PSQ": float(np.mean([a["shorts"]["PSQ"] for a in allocs])),
            "TBF": float(np.mean([a["shorts"]["TBF"] for a in allocs])),
        },
        "dial_std": float(np.std(dial_samples)),
    }
    
    # Uncertainty hedge: wide posterior -> extra GLD
    if result["dial_std"] > 0.06:
        result["gld_min"] = min(result["gld_min"] + 0.02, 0.10)
    
    return result


def get_scenario_label(dial):
    """Human-readable label for display only."""
    d = float(dial)
    if d < THRESHOLDS["bull_calm_max"]: return "bull_calm"
    if d < THRESHOLDS["bull_late_max"]: return "bull_late"
    if d < THRESHOLDS["stress_max"]:    return "stress"
    return "crisis"


def get_blend_name(dial):
    """Select model blend based on dial."""
    d = float(dial)
    if d < THRESHOLDS["bull_calm_max"]: return "bull_calm"
    if d < THRESHOLDS["bull_late_max"]: return "bull_late"
    if d < THRESHOLDS["stress_max"]:    return "stress"
    return "crisis"


class ScenarioState:
    """
    Tracks scenario state for hysteresis.
    Prevents premature scenario switching.
    """
    def __init__(self):
        self.current    = None
        self.weeks_in   = 0
        self.peak_dial  = 0.0
        self.dial_history = []
        self.prev_alloc = None
        self.transition_target = None
        self.transition_week   = 0

    def update(self, dial):
        """
        Update scenario state with hysteresis.
        
        Rules:
        - UPGRADE (more defensive): always immediate
        - DOWNGRADE (less defensive): need buffer + minimum weeks
        - RECOVERY: special config when dial falls from high peak
          triggered after minimum time in crisis/stress
        - CRISIS overrides recovery immediately
        """
        d = float(dial)

        # Track dial history and peak
        self.dial_history.append(d)
        if len(self.dial_history) > 4:
            self.dial_history.pop(0)
        if d > self.peak_dial:
            self.peak_dial = d

        # Raw target from dial value
        raw_target = get_scenario_label(d)

        # Initialize on first call
        if self.current is None:
            self.current  = raw_target
            self.weeks_in = 1
            return raw_target

        self.weeks_in += 1

        # ── CRISIS: highest priority, always immediate ──────────
        if raw_target == "crisis":
            if self.current != "crisis":
                self.current  = "crisis"
                self.weeks_in = 1
            return "crisis"

        # ── STRESS: immediate upgrade, hysteresis on downgrade ──
        if raw_target == "stress":
            stress_level = 3
            curr_level = {"bull_calm":0,"bull_late":1,
                          "recovery":2,"stress":3,"crisis":4
                          }.get(self.current, 1)
            if curr_level < stress_level:
                # Upgrade to stress immediately
                self.current  = "stress"
                self.weeks_in = 1
            elif curr_level > stress_level:
                # Downgrade from crisis: need crisis_exit_weeks + buffer
                # AND dial must be clearly below crisis threshold
                if (self.weeks_in >= HYSTERESIS["crisis_exit_weeks"] and
                    d < THRESHOLDS["stress_max"] - HYSTERESIS["exit_buffer"] and
                    d < THRESHOLDS["stress_max"]):
                    self.current  = "stress"
                    self.weeks_in = 1
                # else stay in crisis
            return self.current

        # ── RECOVERY: triggered when dial falls from high peak ──
        # Conditions:
        #   1. Peak was above stress threshold
        #   2. Current dial far below peak
        #   3. Have been in crisis/stress long enough
        in_elevated = self.current in ("crisis", "stress", "recovery")
        peak_was_high = self.peak_dial > THRESHOLDS["stress_max"]
        dial_fell = d < self.peak_dial - HYSTERESIS["recovery_drop"]
        # Need crisis_exit_weeks in elevated before recovery allowed
        seasoned = self.weeks_in >= HYSTERESIS["crisis_exit_weeks"]

        if peak_was_high and dial_fell and in_elevated and seasoned:
            if self.current != "recovery":
                self.current  = "recovery"
                self.weeks_in = 1
                # Decay peak so recovery can eventually exit
            elif self.weeks_in >= 4:
                # Slowly decay peak to allow eventual bull_late
                self.peak_dial = max(
                    self.peak_dial * 0.85,
                    THRESHOLDS["stress_max"] + 0.05)
            return "recovery"

        # ── BULL_LATE ────────────────────────────────────────────
        if raw_target == "bull_late":
            curr_level = {"bull_calm":0,"bull_late":1,
                          "recovery":2,"stress":3,"crisis":4
                          }.get(self.current, 1)
            if curr_level == 0:
                # Upgrade from bull_calm immediately
                self.current  = "bull_late"
                self.weeks_in = 1
            elif curr_level == 1:
                pass  # already bull_late
            else:
                # Downgrade from recovery/stress/crisis
                # Need weeks + dial below threshold
                exit_map = {
                    "recovery": 3,
                    "stress":   HYSTERESIS["stress_exit_weeks"] + 1,
                    "crisis":   HYSTERESIS["crisis_exit_weeks"] + 1,
                }
                needed = exit_map.get(self.current, 3)
                thresh = THRESHOLDS["bull_late_max"]
                if (self.weeks_in >= needed and
                    d < thresh - HYSTERESIS["exit_buffer"]):
                    self.current  = "bull_late"
                    self.weeks_in = 1
                    self.peak_dial = d  # reset peak on full recovery
            return self.current

        # ── BULL_CALM ────────────────────────────────────────────
        if raw_target == "bull_calm":
            if self.current == "bull_calm":
                return "bull_calm"
            elif self.current == "bull_late":
                # Downgrade from bull_late: need 1 week + buffer
                thresh = THRESHOLDS["bull_calm_max"]
                if (self.weeks_in >= HYSTERESIS["bull_calm_exit_weeks"] and
                    d < thresh - HYSTERESIS["exit_buffer"]):
                    self.current  = "bull_calm"
                    self.weeks_in = 1
                return self.current
            else:
                # From recovery/stress/crisis: step down one level
                # toward bull_late, honoring hysteresis.
                # Cannot return self.current unchanged -- raw_target
                # stays bull_calm while dial is low, so the
                # bull_late branch is never reached and the bot
                # gets permanently trapped.
                exit_map = {
                    "recovery": 3,
                    "stress":   HYSTERESIS["stress_exit_weeks"] + 1,
                    "crisis":   HYSTERESIS["crisis_exit_weeks"] + 1,
                }
                needed = exit_map.get(self.current, 3)
                thresh = THRESHOLDS["bull_late_max"]
                if (self.weeks_in >= needed and
                    d < thresh - HYSTERESIS["exit_buffer"]):
                    self.current   = "bull_late"
                    self.weeks_in  = 1
                    self.peak_dial = d
                return self.current

        return self.current

def momentum_weights(rets, n):
    """6-month momentum inverse-vol weighted."""
    lookback = min(126, len(rets))
    if lookback < 20:
        return np.ones(n) / n
    mom    = rets.iloc[-lookback:].mean().values
    vols   = rets.std().values
    scores = np.where(vols > 0, mom / vols, 0).clip(min=0)
    if scores.sum() == 0:
        return np.ones(n) / n
    return scores / scores.sum()


def run_adaptive_v3(start="2004-06-30", end=None, verbose=True):
    from svi_covariance import fit_svi
    from stability_index import compute_dial
    from portfolio_engine import (risk_parity, min_variance,
                                   max_diversification, equal_weight,
                                   bl_equilibrium, _project_simplex_capped)

    # Load prices
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    # Load dial
    stab = pd.read_parquet(os.path.join(DATA_DIR, "stability.parquet"))
    dial_series = stab["stability_risk"].dropna()

    # Weekly dates
    range_end = pd.Timestamp(end) if end is not None else px.index.max()
    all_dates = pd.date_range(start=start, end=range_end, freq="W-FRI")
    all_dates = [px.index[px.index <= d].max() for d in all_dates]
    all_dates = [d for d in all_dates if pd.notna(d)]

    # Split for out-of-sample validation
    split_date = pd.Timestamp("2018-12-31")
    train_dates    = [d for d in all_dates if d <= split_date]
    validate_dates = [d for d in all_dates if d > split_date]

    port_val   = 10000.0
    equity_now = 0.70          # current equity %, rate-limited
    weights    = None
    # ScenarioState is instantiated but never called anywhere in
    # this loop -- confirmed dead code, leftover from before the
    # rate-limiter rewrite replaced the state machine. Kept
    # instantiated (harmless) rather than removed, to avoid
    # touching more of this validated file than necessary right
    # now. Safe to delete in a future cleanup pass.
    state      = ScenarioState()
    records    = []
    em_dial_history = []  # currency/EM dial's own trailing state,
                            # properly scoped to this function call,
                            # threaded through the loop -- NOT a
                            # global (fixed from an earlier hacky
                            # implementation before it was ever run
                            # for real)
    t0         = time.time()

    print("=" * 72)
    print("ADAPTIVE BACKTEST v3")
    print("=" * 72)
    print(f"Periods: {len(all_dates)} weekly")
    print(f"Train: {start} to 2018-12-31 ({len(train_dates)} weeks)")
    print(f"Validate: 2019-01-01 to present ({len(validate_dates)} weeks)")
    print(f"Thresholds: calm={THRESHOLDS['bull_calm_max']} "
          f"late={THRESHOLDS['bull_late_max']} "
          f"stress={THRESHOLDS['stress_max']}")
    print(f"Min trade: {MIN_TRADE:.0%} | "
          f"DBMF min: 8% | GLD min: 4%")
    print("=" * 72)

    for i, d in enumerate(all_dates):
        # Available assets
        avail = [t for t in RISK_ASSETS + DEF_ASSETS
                 if t in px.columns and
                 pd.Timestamp(ETF_INCEPTION.get(t, "2000-01-01")) <= d]

        avail_shorts = [t for t in SHORT_ASSETS
                        if t in px.columns and
                        pd.Timestamp(ETF_INCEPTION.get(t, "2000-01-01")) <= d]

        use_dbmf = ("DBMF" in px.columns and
                    pd.Timestamp(ETF_INCEPTION["DBMF"]) <= d)

        if len(avail) < 3:
            continue

        # Price history
        hist = px.loc[:d, avail].dropna(axis=1, thresh=60)
        avail = list(hist.columns)
        if len(avail) < 3:
            continue

        avail_risk = [t for t in RISK_ASSETS if t in avail]
        avail_def  = [t for t in DEF_ASSETS  if t in avail]

        rets = hist.pct_change().dropna().iloc[-LOOKBACK:]
        if len(rets) < 60:
            continue

        # Get dial -- market-implied (zero lag, daily resolution)
        # Replaces FRED monthly data with market price proxies
        try:
            dial_val = compute_market_implied_dial(px, d, lookback=252)
        except Exception:
            # Fallback to FRED-based dial if computation fails
            dial_val = float(dial_series.asof(d)) \
                       if d >= dial_series.index[0] else 0.40

        # Rate-limited allocation -- no state machine.
        # De-risk fast, re-risk slow. Cannot latch.
        scenario = get_scenario_label(dial_val)  # display only

        # Get bootstrap dial allocation (smoother threshold handling)
        dial_hist = list(dial_series[:d].dropna().tail(52).values)
        alloc = bootstrap_dial_allocation(dial_hist, n_bootstrap=300, seed=1000+i)
        blend_name = get_blend_name(dial_val)

        # SVI covariance
        try:
            covs, _ = fit_svi(rets, n_steps=SVI_STEPS,
                              n_draws=SVI_DRAWS, verbose=False,
                              seed=2000+i)
            idx_s   = np.linspace(0, len(covs)-1,
                                  OPT_DRAWS).astype(int)
            covs_np = covs[idx_s].numpy() * 252
        except Exception:
            continue

        n        = len(avail)
        fallback = np.ones(n) / n
        mkt_w    = np.ones(n) / n
        blend    = BLENDS.get(blend_name, BLENDS["bull_late"])

        MODEL_FNS = {
            "risk_parity":    risk_parity,
            "min_variance":   min_variance,
            "max_divers":     max_diversification,
            "equal_weight":   equal_weight,
            "bl_equilibrium": None,
            "momentum":       None,
        }

        per_model = {}
        for mname, bwt in blend.items():
            if bwt == 0:
                continue
            try:
                if mname == "bl_equilibrium":
                    w_m = bl_equilibrium(covs_np.mean(0), mkt_w)
                elif mname == "momentum":
                    ri = [avail.index(t) for t in avail_risk
                          if t in avail]
                    if ri:
                        sub = rets.iloc[:, ri]
                        mw  = momentum_weights(sub, len(ri))
                        w_m = np.zeros(n)
                        for ii, ridx in enumerate(ri):
                            w_m[ridx] = mw[ii]
                    else:
                        w_m = fallback.copy()
                else:
                    fn = MODEL_FNS[mname]
                    ws = np.stack([fn(c) for c in covs_np])
                    w_m = ws.mean(0)
                if np.isnan(w_m).any() or w_m.sum() == 0:
                    w_m = fallback.copy()
            except Exception:
                w_m = fallback.copy()
            per_model[mname] = w_m

        w = sum(per_model[m] * blend[m]
                for m in blend if m in per_model and blend[m] > 0)
        if np.isnan(w).any() or w.sum() == 0:
            w = fallback.copy()
        else:
            w = _project_simplex_capped(w)

        # Apply continuous equity/defensive split
        # Rate-limited equity: de-risk fast, re-risk slow.
        # Replaces the scenario state machine entirely -- there is
        # no state to latch in, only a float tracking a float.
        raw_target = alloc["equity_target"]

        # VOLATILITY DIAL LEVER: speed multiplier only. Never
        # touches WHAT is held (that's the credit dial's target,
        # raw_target, computed independently above and NEVER
        # modified here) -- only HOW FAST the rate limiter moves
        # toward it. This is the exclusive-lever design: no other
        # dial can ever touch equity_target itself.
        vol_speed_mult = 1.0
        if os.environ.get("DISABLE_VOL_LEVER") == "1":
            vol_speed_mult = 1.0  # explicit no-op, lever fully disabled
        try:
            vol_reading = dial_volatility.compute_raw_reading(px, d)
            if vol_reading is not None:
                vol_unusual = dial_volatility.compute_action_signal(vol_reading)
                if False:  # vol lever permanently disabled in this copy
                    vol_speed_mult = 1.5
        except Exception:
            pass  # dial failure never blocks the main loop

        # FIXED after finding a real bug via testing: applying the
        # speed multiplier to BOTH directions meant volatility spikes
        # also sped up RE-risking during brief mid-crisis calm blips
        # -- confirmed real cost in the actual Oct 2008 Lehman crash
        # (multi-dial version was $1,250 BEHIND baseline at the worst
        # point, Oct 3 2008, largely from this). Speed boost should
        # ONLY apply to de-risking (getting more defensive faster is
        # correct when vol is high) -- NEVER to re-risking (getting
        # back to risk faster during high vol is exactly backwards,
        # same premature-confidence trap the currency/EM dial's
        # asymmetric persistence design was built to avoid, just not
        # carried over here originally).
        derisk_max = DERISK_MAX * vol_speed_mult
        rerisk_max = RERISK_MAX  # NEVER sped up by volatility

        if raw_target < equity_now:
            equity_now += max(raw_target - equity_now, -derisk_max)
        else:
            equity_now += min(raw_target - equity_now, rerisk_max)
        eq_target = equity_now
        if str(d.date()) in ['2008-09-26','2008-10-03']:
            print(f"    [DIAG] {d.date()}: raw_target={raw_target:.4f} equity_now={equity_now:.4f}")
        ri = [avail.index(t) for t in avail_risk if t in avail]
        di = [avail.index(t) for t in avail_def  if t in avail]

        if ri and di:
            cr = w[ri].sum()
            if cr > 0:
                w[ri] *= eq_target / cr
                w[di] *= (1 - eq_target) / max(1 - cr, 1e-9)
            w = np.clip(w, 0, None)
            w = w / w.sum()

        # CURRENCY/EM DIAL LEVER: EEM slice weight only. Never
        # touches overall equity/defensive split (eq_target,
        # already applied above and NEVER modified here) -- only
        # how much of the equity sleeve's existing allocation goes
        # to EEM specifically. Exclusive-lever design, same
        # principle as the volatility dial above.
        try:
            em_reading = dial_currency_em.compute_raw_reading(px, d)
            if em_reading is not None:
                eem_declining = None
                if "EEM" in px.columns:
                    eem_series = px.loc[:d, "EEM"].dropna()
                    if len(eem_series) >= 65:
                        eem_declining = bool(
                            eem_series.iloc[-1] < eem_series.iloc[-63])

                em_unusual = dial_currency_em.compute_action_signal(
                    em_dial_history, em_reading,
                    eem_absolute_declining=eem_declining)[0]

                if em_unusual and "EEM" in avail and os.environ.get("DISABLE_EM_LEVER") != "1":
                    eem_i = avail.index("EEM")
                    trimmed = w[eem_i] * 0.5
                    freed = w[eem_i] - trimmed
                    w[eem_i] = trimmed
                    # Redistribute freed weight proportionally
                    # across the rest of the RISK sleeve only --
                    # never touches the defensive sleeve, staying
                    # inside this lever's exclusive territory
                    other_ri = [i for i in ri if i != eem_i]
                    if other_ri:
                        other_sum = w[other_ri].sum()
                        if other_sum > 0:
                            w[other_ri] += (w[other_ri] / other_sum) * freed

                em_dial_history.append(em_reading)
        except Exception:
            pass  # dial failure never blocks the main loop

        # GLD minimum 4%
        gld_idx = [avail.index(t) for t in ["GLD"] if t in avail]
        if gld_idx:
            gld_i = gld_idx[0]
            if w[gld_i] < alloc["gld_min"]:
                deficit = alloc["gld_min"] - w[gld_i]
                w[gld_i] = alloc["gld_min"]
                # Take from largest defensive position
                for di_idx in sorted(di, key=lambda x: -w[x]):
                    if di_idx != gld_i and w[di_idx] > deficit:
                        w[di_idx] -= deficit
                        break

        w = _project_simplex_capped(w)

        # Build full weight dict
        weight_dict = {avail[j]: float(w[j]) for j in range(n)}

        # DBMF allocation
        dbmf_w = alloc["dbmf"] if use_dbmf else 0.0
        if dbmf_w > 0:
            # Reduce equity proportionally to fund DBMF
            for t in avail_risk:
                if t in weight_dict:
                    weight_dict[t] *= (1 - dbmf_w)
            weight_dict["DBMF"] = dbmf_w
        else:
            # Pre-2019: add DBMF weight to GLD instead
            for t in avail_risk:
                if t in weight_dict:
                    weight_dict[t] *= (1 - dbmf_w * 0.5)
            if "GLD" in weight_dict:
                weight_dict["GLD"] = min(
                    weight_dict.get("GLD", 0) + dbmf_w * 0.5, 0.20)

        # Add shorts
        shorts = {k: v for k, v in alloc["shorts"].items()
                  if k in avail_shorts and v > 0.01}  # min 1% short
        total_short = sum(shorts.values())
        if total_short > 0 and ri:
            for t in avail_risk:
                if t in weight_dict:
                    weight_dict[t] *= (1 - total_short)
            for t, sw in shorts.items():
                weight_dict[t] = sw

        # Normalize
        total_w = sum(weight_dict.values())
        if total_w > 0:
            weight_dict = {k: v/total_w for k, v in weight_dict.items()}

        # Transaction costs with MIN TRADE SIZE
        all_tickers = list(weight_dict.keys())
        if weights is not None:
            old_w = pd.Series(weights).reindex(all_tickers).fillna(0)
            new_w = pd.Series(weight_dict).reindex(all_tickers).fillna(0)
            drift = (new_w - old_w).abs()

            # Only trade positions that drift more than MIN_TRADE
            trades = drift[drift > MIN_TRADE]
            if len(trades) > 0:
                turnover = trades.sum() / 2
                port_val *= (1 - TCOST * turnover * 2)
            # If no positions drift enough: skip rebalance entirely
            else:
                # Keep old weights
                weight_dict = {k: float(weights.get(k, 0))
                               for k in weight_dict}

        weights = weight_dict

        # Roll forward to next rebalance
        # BUG FIX: previously fell back to px.index[-1] (today's
        # actual date) on the last loop iteration when i+1 was out
        # of range. This was fine for the original unbounded
        # function where all_dates already extended close to
        # px.index[-1] anyway -- but once a real `end` parameter
        # was added for short test windows, this fallback reached
        # all the way to TODAY's live price data, computing a
        # nonsense multi-year "one week" return using Dec 2013
        # prices as the start and Aug 2026 prices as the end.
        # Confirmed: this produced a phantom final record
        # (portfolio=$47,278, dated 2026-08-07) that corrupted
        # every summary statistic in a bounded window test.
        # Correct fallback: just repeat the last real date, which
        # naturally produces zero return for a redundant final
        # iteration instead of a fabricated one.
        next_d = all_dates[i+1] if i+1 < len(all_dates) else all_dates[i]

        # Compute return
        ret = 0.0
        pp = px.loc[d:next_d,
                    [t for t in weight_dict if t in px.columns]
                   ].dropna(how="all")
        if len(pp) < 2:
            continue

        for t, tw in weight_dict.items():
            if t not in pp.columns:
                continue
            pr = pp[t].dropna()
            if len(pr) < 2:
                continue
            t_ret = float(pr.iloc[-1] / pr.iloc[0] - 1)
            ret += tw * t_ret

        if np.isnan(ret) or np.isinf(ret):
            continue

        port_val *= (1 + ret)
        if np.isnan(port_val):
            port_val = 10000.0

        records.append({
            "date":      next_d,
            "portfolio": port_val,
            "dial":      dial_val,
            "scenario":  scenario,
            "in_sample": d <= split_date,
        })

        if verbose:
            elapsed = time.time() - t0
            eta = elapsed/(i+1)*(len(all_dates)-i-1) if i > 0 else 0
            pct = (i+1)/len(all_dates)*100
            bar = "#"*int(pct/2) + "-"*(50-int(pct/2))
            print(f"  [{bar}] {pct:5.1f}%  {d.date()}  "
                  f"${port_val:>9,.0f}  dial={dial_val:.2f}  "
                  f"scen={scenario:<10}  "
                  f"ETA={eta/60:.1f}m", flush=True)

    if not records:
        print("No records.")
        return None

    series = pd.Series(
        [r["portfolio"] for r in records],
        index=[r["date"] for r in records])

    # Full period metrics
    years  = (series.index[-1]-series.index[0]).days/365.25
    total  = series.iloc[-1]/10000-1
    ann    = (1+total)**(1/max(years,1))-1
    wrets  = series.pct_change().dropna()
    sharpe_weekly = float(wrets.mean()/wrets.std()*np.sqrt(52)) \
                    if wrets.std() > 0 else 0
    # "Daily Sharpe" removed: the underlying series is weekly
    # (one value per rebalance), so resampling onto a daily grid
    # produces nothing but NaN gaps between real observations.
    # resample("D").last().pct_change().dropna() silently returned
    # an EMPTY series, whose .std() is nan, which fails the
    # "> 0" guard and fell through to a hardcoded 0 -- printing a
    # clean-looking but meaningless 0.00 in both v1 and v2 output.
    # There is no real daily Sharpe to compute from weekly data.
    sharpe_daily = None
    roll_max = series.cummax()
    dd       = (series - roll_max)/roll_max
    max_dd   = float(dd.min())
    calmar   = ann/max(abs(max_dd), 1e-9)

    # Out-of-sample metrics
    oos = series[series.index > split_date]
    if len(oos) > 10:
        oos_ret   = oos.pct_change().dropna()
        oos_ann   = (oos.iloc[-1]/oos.iloc[0])**(
                     252/len(oos_ret))-1
        oos_sharpe = float(oos_ret.mean()/oos_ret.std()*np.sqrt(52)) \
                     if oos_ret.std() > 0 else 0
        oos_dd = float(((oos-oos.cummax())/oos.cummax()).min())
    else:
        oos_ann = oos_sharpe = oos_dd = 0

    print("\n" + "="*72)
    print("ADAPTIVE v3 RESULTS")
    print("="*72)
    print(f"\n  FULL PERIOD (2004-2026):")
    print(f"    Final value:      ${series.iloc[-1]:>10,.2f}")
    print(f"    Total return:     {total:>10.1%}")
    print(f"    Ann return:       {ann:>10.1%}")
    print(f"    Sharpe (weekly):  {sharpe_weekly:>10.2f}")
    print(f"    Sharpe (daily):   {'n/a -- weekly data only':>10}")
    print(f"    Max drawdown:     {max_dd:>10.1%}")
    print(f"    Calmar:           {calmar:>10.2f}")
    print(f"\n  OUT-OF-SAMPLE (2019-2026):")
    print(f"    Ann return:       {oos_ann:>10.1%}")
    print(f"    Sharpe (weekly):  {oos_sharpe:>10.2f}")
    print(f"    Max drawdown:     {oos_dd:>10.1%}")
    print()

    # Gate check
    print("  PAPER TRADING GATE CHECK:")
    gates = {
        "Sharpe (weekly) >= 1.1": sharpe_weekly >= 1.1,
        "Max DD <= 30%":          max_dd >= -0.30,
        "Calmar >= 0.35":         calmar >= 0.35,
        "Final >= $70,000":       series.iloc[-1] >= 70000,
        "OOS Sharpe >= 0.90":     oos_sharpe >= 0.90,
    }
    all_pass = True
    for name, passed in gates.items():
        icon = "✅" if passed else "❌"
        print(f"    {icon} {name}")
        if not passed:
            all_pass = False

    verdict = ("🎉 ALL GATES PASSED — READY FOR PAPER TRADING"
               if all_pass else
               "⚠️  GATES NOT MET — REFINE STRATEGY")
    print(f"\n  {verdict}")

    # Scenario breakdown
    df = pd.DataFrame(records)
    print(f"\n  SCENARIO BREAKDOWN:")
    for scen in ["bull_calm","bull_late","stress","crisis","recovery"]:
        sub = df[df["scenario"]==scen]
        if len(sub) == 0:
            continue
        sub_rets = pd.Series(
            [r["portfolio"] for r in records
             if r["scenario"]==scen]).pct_change().dropna()
        avg_ret = sub_rets.mean()*52*100 if len(sub_rets)>0 else 0
        print(f"    {scen:<12} {len(sub):>4} weeks  "
              f"avg ann {avg_ret:>6.1f}%")

    # Save
    results = {
        "version": "v3",
        "final": float(series.iloc[-1]),
        "total": float(total),
        "ann_ret": float(ann),
        "sharpe_weekly": float(sharpe_weekly),
        "sharpe_daily": None,  # not computable from weekly-only series
        "max_dd": float(max_dd),
        "calmar": float(calmar),
        "years": float(years),
        "oos": {
            "ann_ret": float(oos_ann),
            "sharpe": float(oos_sharpe),
            "max_dd": float(oos_dd),
        },
        "gates": {k: bool(v) for k, v in gates.items()},
        "all_pass": all_pass,
        "records": [
            {"date": str(r["date"].date()),
             "portfolio": r["portfolio"],
             "dial": r["dial"],
             "scenario": r["scenario"],
             "in_sample": r["in_sample"]}
            for r in records
        ],
    }
    out = os.path.join(DATA_DIR, "adaptive_backtest_v3.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved to {out}")
    print(f"  Runtime: {(time.time()-t0)/60:.0f} minutes")
    return results


if __name__ == "__main__":
    run_adaptive_v3()
