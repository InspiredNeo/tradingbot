"""
Volatility dial -- second of the four independent dials.

Design: same template as dial_currency_em.py, proven through real
debugging. VIX is a direct, absolute measure (not a ratio/spread
between two assets), so it should be less prone to the "both
sides moving the same direction, different speed" blind spot
found and fixed in the currency/EM dial -- worth confirming this
via testing, not assuming it.

This dial's exclusive lever (per the finalized multi-dial design):
rate-limiter SPEED -- how fast the credit dial's equity/defensive
target gets approached, not WHAT is held. High vol = move faster
toward whatever the credit dial has already decided.
"""
import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")


def compute_raw_reading(px, date, lookback=252):
    """
    Raw volatility reading -- ALWAYS computed, every week.
    Direct VIX level, percentile-ranked against its own trailing
    history (same percentile-rank approach as the currency/EM
    dial, proven to work there).
    """
    if "^VIX" not in px.columns:
        return None

    vix = px.loc[:date, "^VIX"].dropna()
    if len(vix) < 60:
        return None

    hist = vix.iloc[-lookback:] if len(vix) >= lookback else vix
    if len(hist) < 10:
        return None

    current = float(vix.iloc[-1])
    reading = float((hist < current).mean())  # percentile rank, 0-1
    return reading


def validate_signal_separation(px, verbose=True):
    """
    Same real validation as the currency/EM dial -- does this
    signal actually separate known-stressed from known-calm
    periods by a meaningful margin.
    """
    STRESSED_PERIODS = [
        ("2008-09-01", "2008-12-31", "2008 crisis peak"),
        ("2020-02-15", "2020-04-15", "COVID crash"),
        ("2018-01-25", "2018-02-15", "Volmageddon"),
    ]
    CALM_PERIODS = [
        ("2005-01-01", "2005-12-31", "Calm mid-2000s"),
        ("2017-01-01", "2017-12-31", "Quiet bull market"),
        ("2013-01-01", "2013-03-01", "Pre-Taper-Tantrum calm"),
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


def compute_action_signal(current_reading, absolute_bar=0.699):
    """
    ACTION layer, using the proven currency/EM template directly:
    absolute bar anchored to real calm-period history (not the
    stressed median, which caused false releases mid-crisis in
    the first dial -- same fix applied here from the start,
    learned once, not rediscovered).
    """
    return current_reading >= absolute_bar


def simulate_action_layer(px, dates, verbose=True):
    """
    Same trailing-window persistence logic proven in the
    currency/EM dial: 4-week window, 75% to engage, 25% to
    release. Asymmetric, tolerant of single-week noise in
    either direction.
    """
    is_unusual_window = []
    WINDOW = 4
    ENGAGE_FRACTION = 0.75
    RELEASE_FRACTION = 0.25

    action_engaged = False
    results = []

    for d in dates:
        reading = compute_raw_reading(px, d)
        if reading is None:
            continue

        is_unusual = compute_action_signal(reading)
        is_unusual_window.append(is_unusual)
        is_unusual_window = is_unusual_window[-WINDOW:]

        if len(is_unusual_window) >= WINDOW:
            frac_unusual = sum(is_unusual_window) / WINDOW
            if not action_engaged and frac_unusual >= ENGAGE_FRACTION:
                action_engaged = True
            elif action_engaged and frac_unusual <= RELEASE_FRACTION:
                action_engaged = False

        results.append({
            "date": d, "reading": reading,
            "action_engaged": action_engaged,
        })

        if verbose:
            flag = "  <- ACTION" if action_engaged else ""
            print(f"  {d.date()}: reading={reading:.3f}{flag}")

    return results


if __name__ == "__main__":
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)
    validate_signal_separation(px)
