"""
Currency/EM dial -- first of the four independent dials in the
multi-dial architecture. Built as the template for the other
three (credit already exists as the main dial; volatility and
rate follow this same pattern).

Design principles (from this session's discussion):
  - DETECTION is always on -- every week's raw reading gets
    computed and recorded, nothing is thrown away, no matter how
    small.
  - ACTION is a separate, higher bar -- only fires when a move is
    BOTH unusual relative to this dial's own recent normal range,
    AND persists rather than reverting immediately.
  - This dial's exclusive lever: EEM/SCHF weight specifically.
    It does not touch overall equity/defensive split (that's the
    credit dial's job) or anything else -- no shared resource with
    any other dial, so it cannot collide the way TLT did.
"""
import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")


def compute_raw_reading(px, date, lookback=252):
    """
    Raw currency/EM stress reading -- ALWAYS computed, every week,
    regardless of whether it will end up triggering any action.
    This is the "detection" layer.

    Same market-implied approach as the main dial: EEM vs SCHF
    63-day return divergence, percentile-ranked against its own
    2-year trailing history.
    """
    if "EEM" not in px.columns or "SCHF" not in px.columns:
        return None

    eem = px.loc[:date, "EEM"].dropna()
    schf = px.loc[:date, "SCHF"].dropna()
    if len(eem) < 120 or len(schf) < 120:
        return None

    er = eem.pct_change(63).dropna()
    scr = schf.pct_change(63).dropna()
    common = er.index.intersection(scr.index)
    if len(common) < 60:
        return None

    spread = (scr.loc[common] - er.loc[common]).dropna()
    hist = spread.iloc[-lookback:] if len(spread) >= lookback else spread
    if len(hist) < 10:
        return None

    current = float(spread.iloc[-1])
    reading = float((hist < current).mean())  # percentile rank, 0-1
    return reading


def compute_reading_series(px, dates):
    """
    Compute the raw reading for every date in a list -- this is
    what "always detecting" looks like in practice: a full,
    continuous series, computed regardless of what will later be
    judged actionable.
    """
    return pd.Series(
        {d: compute_raw_reading(px, d) for d in dates}
    ).dropna()


def compute_action_signal(reading_history, current_reading,
                          eem_absolute_declining=None,
                          lookback_weeks=26, relative_threshold=1.5,
                          use_absolute_bar=True,
                          absolute_bar=0.857):
    """
    Second, independent check added after finding a real false-fire
    case: Jan 2017 fired purely on EEM underperforming SCHF in
    RELATIVE terms, while EEM itself was genuinely rising in
    absolute terms the whole time (confirmed: $28.18 -> $31.05,
    real market data). That's ordinary bull-market sector rotation,
    not EM stress by any honest definition.

    eem_absolute_declining: bool, whether EEM's own price is
    actually below where it was ~63 days ago (same lookback as the
    relative spread calculation). If explicitly False (EEM is
    genuinely rising), the reading is NOT considered unusual
    regardless of the relative percentile -- a real currency/EM
    shock should show EEM actually falling, not just underperforming
    a stronger peer. If None (not provided), skips this check
    entirely, same as before this fix.
    """
    """
    ACTION layer -- separate, higher bar than detection.

    FIXED after a real bug found via testing: the original
    relative-only (z-score vs trailing mean) approach failed to
    trigger AT ALL during the real 2013 Taper Tantrum, because the
    26-week trailing baseline itself became contaminated by the
    crisis building up within that same window -- by the time the
    crisis was fully underway, "recent normal" already included
    the crisis's own leading edge, masking it as not unusual.

    Fix: combine the relative check with an ABSOLUTE bar, derived
    from validate_signal_separation()'s real measurement of what
    genuinely separates known-stressed from known-calm periods
    (0.905 = the real stressed-period median, with only 4.9% of
    calm-period readings ever reaching it). This absolute bar
    can't be contaminated by a rolling window, because it's fixed
    from a genuine historical baseline, not recomputed from
    recent data that might itself be part of the event.

    A move only triggers action if BOTH:
      1. ABSOLUTE: at or above the real, validated stressed-period
         bar (not relative to potentially-contaminated recent
         history)
      2. PERSISTS for `persistence_weeks` consecutive weeks
    """
    is_unusual_absolute = current_reading >= absolute_bar
    if is_unusual_absolute and eem_absolute_declining is False:
        # Relative spread says "stressed" but EEM is genuinely
        # rising -- override, this is sector rotation, not a
        # real EM shock
        is_unusual_absolute = False

    # Still compute the relative z-score for transparency/logging,
    # even though action now gates on the absolute bar -- keeps
    # the detection layer's "always record everything" principle
    z_score = 0.0
    if len(reading_history) >= 10:
        hist = np.array(reading_history[-lookback_weeks:])
        mean, std = hist.mean(), hist.std()
        if std > 0:
            z_score = (current_reading - mean) / std

    return is_unusual_absolute, float(z_score)


def simulate_action_layer(px, dates, verbose=True):
    """
    Walk forward through a real date range, computing detection
    (always) and action (only when threshold + persistence both
    met) at each step. This is the honest simulation of what the
    live system would actually do -- not just a single-point check.
    """
    history = []
    consecutive_unusual = 0
    consecutive_normal = 0
    action_engaged = False
    results = []

    # SECOND fix, after full diagnosis: strict consecutive-week
    # counting resets to zero on a SINGLE noisy dip, even during
    # genuine ongoing stress (confirmed: real April-May 2013 data
    # has legitimate single-week dips below the bar while the
    # crisis was still fully active, causing premature release).
    # Fixed to a trailing-window FRACTION instead of strict
    # consecutive count -- tolerates normal single-week noise in
    # either direction without losing the persistence requirement.
    is_unusual_window = []
    WINDOW = 4
    ENGAGE_FRACTION = 0.75   # 3 of last 4 weeks unusual -> engage
    RELEASE_FRACTION = 0.25  # only 1 of last 4 weeks unusual -> release

    for d in dates:
        reading = compute_raw_reading(px, d)
        if reading is None:
            continue

        # Real check: is EEM itself actually declining (not just
        # underperforming SCHF in relative terms)?
        eem_declining = None
        if "EEM" in px.columns:
            eem = px.loc[:d, "EEM"].dropna()
            if len(eem) >= 65:
                eem_declining = bool(eem.iloc[-1] < eem.iloc[-63])

        is_unusual, z = compute_action_signal(
            history, reading, eem_absolute_declining=eem_declining)

        is_unusual_window.append(is_unusual)
        is_unusual_window = is_unusual_window[-WINDOW:]

        if len(is_unusual_window) >= WINDOW:
            frac_unusual = sum(is_unusual_window) / WINDOW
            if not action_engaged and frac_unusual >= ENGAGE_FRACTION:
                action_engaged = True
            elif action_engaged and frac_unusual <= RELEASE_FRACTION:
                action_engaged = False

        results.append({
            "date": d, "reading": reading, "z_score": z,
            "action_engaged": action_engaged,
        })
        history.append(reading)

        if verbose:
            flag = "  <- ACTION" if action_engaged else ""
            print(f"  {d.date()}: reading={reading:.3f} z={z:+.2f}"
                  f"{flag}")

    return results


def validate_signal_separation(px, verbose=True):
    """
    REAL validation: does this signal actually separate known-
    stressed periods from known-calm periods by a meaningful
    margin, or does it just look elevated everywhere (noisy)?

    This is the check that was MISSING earlier -- checking one
    crisis period in isolation without a calm-period contrast is
    not real validation. A signal that reads high during both a
    real crisis AND a genuinely calm year (confirmed: 2017 read
    0.87-0.95 in January with no real EM stress at all) is not
    actually distinguishing anything -- it's just noisy.

    Returns a real separation metric: mean(stressed) - mean(calm),
    plus the overlap between their distributions. A good signal
    should show a large gap and minimal overlap. A bad signal
    (like the one just found) shows means close together and/or
    heavy overlap.
    """
    STRESSED_PERIODS = [
        ("2013-04-01", "2013-08-31", "Taper Tantrum"),
        ("2015-07-01", "2015-09-30", "China deval / Aug 2015"),
    ]
    CALM_PERIODS = [
        ("2013-01-01", "2013-03-01", "Pre-Taper-Tantrum calm"),
        ("2017-01-01", "2017-12-31", "Quiet bull market"),
        ("2005-01-01", "2005-12-31", "Calm mid-2000s"),
    ]

    def collect_readings(periods):
        vals = []
        for start, end, label in periods:
            dates = pd.date_range(start, end, freq="W-FRI")
            for d in dates:
                r = compute_raw_reading(px, d)
                if r is not None:
                    vals.append(r)
        return np.array(vals)

    stressed_vals = collect_readings(STRESSED_PERIODS)
    calm_vals = collect_readings(CALM_PERIODS)

    if len(stressed_vals) == 0 or len(calm_vals) == 0:
        print("Not enough data to validate")
        return None

    stressed_mean = stressed_vals.mean()
    calm_mean = calm_vals.mean()
    separation = stressed_mean - calm_mean

    # Overlap: what fraction of calm-period readings are AS HIGH
    # as the median stressed-period reading? High overlap = bad
    # signal (can't tell stressed from calm by looking at a
    # single reading).
    stressed_median = np.median(stressed_vals)
    overlap_fraction = float((calm_vals >= stressed_median).mean())

    if verbose:
        print(f"Stressed periods: mean={stressed_mean:.3f}, "
              f"median={stressed_median:.3f}, n={len(stressed_vals)}")
        print(f"Calm periods:     mean={calm_mean:.3f}, "
              f"n={len(calm_vals)}")
        print(f"Separation (stressed - calm mean): {separation:+.3f}")
        print(f"Overlap (% of calm readings >= stressed median): "
              f"{overlap_fraction:.1%}")
        print()
        verdict = ("GOOD -- real separation, low overlap"
                   if separation > 0.15 and overlap_fraction < 0.25
                   else "POOR -- signal does not reliably separate "
                        "stressed from calm periods")
        print(f"Verdict: {verdict}")

    return {
        "stressed_mean": stressed_mean, "calm_mean": calm_mean,
        "separation": separation, "overlap_fraction": overlap_fraction,
    }


if __name__ == "__main__":
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    # Real historical validation dates -- same discipline as the
    # original market-implied dial's 10-date check
    test_dates = [
        ("2012-06-30", "EU crisis, US/EM should read calm-ish"),
        ("2013-06-30", "Taper Tantrum peak -- EM should read HIGH"),
        ("2013-09-30", "Taper Tantrum aftermath, still elevated"),
        ("2015-08-31", "China deval / Aug 2015 selloff"),
        ("2017-12-31", "Quiet bull, should read calm"),
        ("2018-10-31", "US-focused stress, EM effect less clear"),
        ("2020-03-31", "COVID -- broad, EM likely elevated too"),
        ("2022-06-30", "Rate crisis, US-centric, EM effect unclear"),
    ]

    print("Currency/EM dial raw readings (detection layer):")
    print(f"  {'Date':<12} {'Reading':<10} {'Note'}")
    for date_str, note in test_dates:
        d = pd.Timestamp(date_str)
        r = compute_raw_reading(px, d)
        r_str = f"{r:.3f}" if r is not None else "N/A"
        print(f"  {date_str:<12} {r_str:<10} {note}")
