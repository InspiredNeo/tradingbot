"""
Combined regime detector: breadth + correlation, the two-part
signal replacing the single scalar dial approach. Validated
separately (breadth: 86.5pp separation, correlation: 24.5pp
separation but genuinely complements breadth's blind spot rather
than needing a fix -- confirmed via real data at 2013-06-15,
where high correlation coincided with still-positive average
returns, correctly read as "correlated calm/mild rotation" not
"correlated crisis").

Four real, distinct regimes based on the combination, not a
single blended number:
  LOW breadth stress + LOW correlation  = genuine calm
  LOW breadth stress + HIGH correlation = correlated calm/mild
                                           rotation (e.g. June 2013)
  HIGH breadth stress + LOW correlation = scattered/idiosyncratic
                                           weakness, not systemic
  HIGH breadth stress + HIGH correlation = genuine systemic crisis
                                           (highest confidence signal)
"""
import os
import pandas as pd
import json

from market_breadth import compute_breadth
from market_correlation import compute_correlation

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")

# Thresholds derived from the real validation data:
# breadth stressed avg 96.6%, calm avg 10.2% -- midpoint-ish,
# biased toward the calm side since calm dates clustered tightly
# (4.7-22.8%) while stressed dates clustered even more tightly
# (94.6-98.1%) -- a wide gap to place a threshold in safely
BREADTH_STRESS_THRESHOLD = 0.40

# FIXED after finding a real calibration problem: breadth alone
# has a natural saturation issue -- it separates calm from
# not-calm cleanly (4.7% vs 78%+) but plateaus in a narrow band
# (78-98%) regardless of whether the real event is a mild credit
# crunch or an acute systemic crisis. avg_deviation (how FAR below
# the moving average, not just how many are below) shows a much
# cleaner real gradient: mild events cluster -3% to -12%, acute
# crises cluster -26% to -32%, with a genuine, clean gap between
# them in real historical data. Severity now gated on deviation,
# not breadth count.
SEVERE_DEVIATION_THRESHOLD = -0.18  # placed in the real, empty gap
                                     # between -12% (mild) and -26%
                                     # (acute), confirmed via direct
                                     # historical measurement

# correlation stressed avg 0.833, calm avg 0.588 -- real but
# weaker separation, threshold placed conservatively
CORR_HIGH_THRESHOLD = 0.70


# Persistence-based severity, added after finding a real gap:
# a single week's deviation alone missed the entire 9-month 2022
# bear market (never crossed the sudden-crash threshold in any
# single week, despite breadth staying above 80% for months).
# Real fix: SYSTEMIC_CRISIS now triggers on EITHER a sudden severe
# spike OR sustained elevated breadth over time -- same asymmetric
# persistence principle already validated for the currency/EM dial.
PERSISTENT_STRESS_WEEKS = 8   # trailing window size
PERSISTENT_BREADTH_THRESHOLD = 0.75  # breadth level counted as
                                       # "elevated" for persistence
# FIXED after finding real flickering in the 2022 test: strict
# "ALL 8 of the last 8 weeks elevated" reset on a single relief
# week (e.g. Aug 12 2022 dipped to 66.3%), causing the crisis
# label to flicker on/off during what was, in real history, one
# continuous ongoing bear market. Same fix already proven for the
# currency/EM dial: trailing-window FRACTION instead of strict
# all-weeks requirement, tolerant of single-week noise.
PERSISTENT_ENGAGE_FRACTION = 0.75  # 6 of 8 weeks elevated -> escalate
PERSISTENT_RELEASE_FRACTION = 0.25  # only 2 of 8 weeks elevated -> release


def detect_regime(px, date, universe, breadth_history=None, previously_severe=None,
                  corr_history=None, previously_corr_high=None, regime_history=None,
                  raw_regime_history=None):
    """
    breadth_history: list of recent pct_below readings, oldest to
    newest, threaded through by the caller (same pure-function
    pattern as every other stateful check this session -- no
    internal state stored here).
    """
    breadth = compute_breadth(px, date, universe)
    corr = compute_correlation(px, date)

    if breadth is None or corr is None:
        return None

    breadth_stressed = breadth["pct_below"] >= BREADTH_STRESS_THRESHOLD
    sudden_severe = breadth["avg_deviation"] <= SEVERE_DEVIATION_THRESHOLD

    # Persistence check with hysteresis, same asymmetric pattern
    # already validated for the currency/EM dial: engage on a
    # trailing-window FRACTION (tolerant of single noisy weeks),
    # release only when the fraction drops much further --
    # prevents the flickering found in the strict-all-weeks version.
    sustained_severe = False
    if breadth_history is not None and len(breadth_history) >= PERSISTENT_STRESS_WEEKS:
        recent = breadth_history[-PERSISTENT_STRESS_WEEKS:]
        elevated_fraction = sum(1 for b in recent if b >= PERSISTENT_BREADTH_THRESHOLD) / len(recent)
        was_already_severe = (previously_severe if previously_severe is not None else False)
        if not was_already_severe and elevated_fraction >= PERSISTENT_ENGAGE_FRACTION:
            sustained_severe = True
        elif was_already_severe and elevated_fraction >= PERSISTENT_RELEASE_FRACTION:
            sustained_severe = True  # stay engaged, hasn't dropped enough to release
        else:
            sustained_severe = False

    severely_stressed = sudden_severe or sustained_severe

    # Same hysteresis fix applied to correlation, for the same
    # reason: a single week's correlation dip (e.g. Sept 16-23 2022,
    # right in the middle of an otherwise-correctly-sustained
    # crisis) was causing brief SCATTERED_WEAKNESS interruptions
    # even while breadth correctly stayed engaged underneath.
    corr_high_raw = corr["avg_correlation"] >= CORR_HIGH_THRESHOLD
    if corr_history is not None and len(corr_history) >= 3:
        recent_corr = corr_history[-3:]
        was_corr_high = (previously_corr_high if previously_corr_high is not None else False)
        elevated_corr_fraction = sum(1 for c in recent_corr if c >= CORR_HIGH_THRESHOLD) / len(recent_corr)
        if not was_corr_high and elevated_corr_fraction >= 0.67:
            corr_high = True
        elif was_corr_high and elevated_corr_fraction >= 0.34:
            corr_high = True  # stay engaged, hasn't dropped enough
        else:
            corr_high = False
    else:
        corr_high = corr_high_raw

    if not breadth_stressed and not corr_high:
        raw_regime = "CALM"
    elif not breadth_stressed and corr_high:
        raw_regime = "CORRELATED_CALM"
    elif breadth_stressed and not severely_stressed:
        raw_regime = "MODERATE_STRESS"
    elif breadth_stressed and not corr_high:
        raw_regime = "SCATTERED_WEAKNESS"
    else:
        raw_regime = "SYSTEMIC_CRISIS"

    # THIRD fix, applied at the right level this time: the two
    # underlying signals (breadth, correlation) each got their own
    # hysteresis, but disagreement in their TIMING still flickered
    # the COMBINED label (confirmed: fixing breadth's flicker moved
    # the problem to correlation's, fixing that moved it again).
    # Real fix: persistence on the FINAL combined regime itself,
    # not just its two inputs separately. Once SYSTEMIC_CRISIS is
    # reached, require the raw combination to genuinely leave that
    # classification for several consecutive weeks before actually
    # exiting -- a brief, single-week disagreement between the two
    # underlying signals shouldn't flip the final label.
    # FIXED: previous logic had a genuine permanent-latch bug --
    # the inner check re-tested the exact same condition already
    # confirmed true by was_crisis, making the release branch
    # unreachable dead code. Once regime_history[-1] was
    # SYSTEMIC_CRISIS, output was ALWAYS SYSTEMIC_CRISIS forever,
    # confirmed directly: real backtest got stuck through breadth
    # readings as low as 0.32 (deep calm territory) in May 2008,
    # unable to ever exit. Same category of bug as the original
    # ScenarioState latches found early this session.
    #
    # Real fix: trailing-window FRACTION on the raw regime
    # classification itself, same proven pattern as every other
    # persistence check tonight. Requires most (not all, not just
    # one) of the recent raw readings to genuinely leave crisis
    # before actually releasing -- tolerant of real volatility
    # without being permanently stuck.
    CRISIS_RELEASE_WINDOW = 4
    CRISIS_RELEASE_FRACTION = 0.75  # 3 of last 4 raw readings must
                                      # be non-crisis to actually exit

    if regime_history is not None and len(regime_history) >= 1:
        was_crisis = regime_history[-1] == "SYSTEMIC_CRISIS"
    else:
        was_crisis = False

    # DECISIVE_CALM_THRESHOLD: a breadth reading this low is
    # unambiguous enough to release immediately, without waiting
    # out the full persistence window -- avoids making genuinely
    # dramatic, clear improvement wait an arbitrary number of
    # weeks just because that's the window size chosen for
    # ambiguous, borderline cases.
    DECISIVE_CALM_THRESHOLD = 0.15  # well below BREADTH_STRESS_THRESHOLD
                                      # (0.40), a real, unambiguous margin

    if not was_crisis:
        regime = raw_regime
    elif raw_regime == "SYSTEMIC_CRISIS":
        regime = "SYSTEMIC_CRISIS"  # still crisis, no ambiguity
    elif breadth["pct_below"] <= DECISIVE_CALM_THRESHOLD:
        # Fast exit: this week's reading is decisively, unambiguously
        # calm -- release immediately rather than waiting out the
        # full multi-week persistence window
        regime = raw_regime
    else:
        # Ambiguous/borderline improvement -- still needs the full
        # persistence window before actually releasing
        if raw_regime_history is not None and len(raw_regime_history) >= CRISIS_RELEASE_WINDOW:
            recent = raw_regime_history[-CRISIS_RELEASE_WINDOW:]
            non_crisis_fraction = sum(1 for r in recent if r != "SYSTEMIC_CRISIS") / len(recent)
            if non_crisis_fraction >= CRISIS_RELEASE_FRACTION:
                regime = raw_regime
            else:
                regime = "SYSTEMIC_CRISIS"
        else:
            regime = "SYSTEMIC_CRISIS"

    return {
        "regime": regime,
        "pct_below": breadth["pct_below"],
        "avg_deviation": breadth["avg_deviation"],
        "avg_correlation": corr["avg_correlation"],
        "severely_stressed": severely_stressed,  # thread forward as
                                                    # previously_severe
                                                    # on the next call
        "corr_high": corr_high,  # thread forward as previously_corr_high
        "raw_regime": raw_regime,  # thread forward, append to raw_regime_history
    }


if __name__ == "__main__":
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    with open(os.path.join(DATA_DIR, "final_equity_universe.json")) as f:
        universe = json.load(f)

    TEST_DATES = [
        ("2008-11-15", "2008 crisis depth -- expect SYSTEMIC_CRISIS"),
        ("2009-02-27", "2008-09 crisis trough -- expect SYSTEMIC_CRISIS"),
        ("2020-03-20", "COVID crash -- expect SYSTEMIC_CRISIS"),
        ("2022-06-15", "2022 rate crisis -- expect SYSTEMIC_CRISIS"),
        ("2013-06-15", "Taper Tantrum peak -- expect CORRELATED_CALM (real, validated case)"),
        ("2005-06-15", "calm mid-2000s -- expect CALM"),
        ("2017-06-15", "calm mid-2017 -- expect CALM"),
        ("2021-06-15", "calm mid-2021 -- expect CALM"),
    ]

    print(f"{'Date':<12} {'Regime':<20} {'pct_below':<10} {'avg_corr':<10} {'Note'}")
    for date_str, note in TEST_DATES:
        d = pd.Timestamp(date_str)
        result = detect_regime(px, d, universe)
        if result:
            print(f"{date_str:<12} {result['regime']:<20} "
                  f"{result['pct_below']:<10.1%} {result['avg_correlation']:<10.3f} {note}")
        else:
            print(f"{date_str:<12} FAILED TO COMPUTE")
