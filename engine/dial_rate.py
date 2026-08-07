"""
Rate dial -- third of the four independent dials.

Design: same proven template. TLT/SHY ratio is a relative
comparison between two assets (like currency/EM's EEM/SCHF), NOT
an absolute measure like volatility's VIX -- so it may share the
same "both sides moving the same direction, different speed"
blind spot found and fixed in the currency/EM dial. Worth testing
for this specifically, not assuming either way.

This dial's exclusive lever (per the finalized multi-dial design):
TBF/duration hedge exposure -- its own small, dedicated sleeve,
separate from the main equity sleeve and the EM slice.
"""
import os
import pandas as pd
import numpy as np

DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")


def compute_raw_reading(px, date, lookback=252):
    """
    Raw rate-stress reading -- ALWAYS computed, every week.
    TLT/SHY ratio (long vs short duration), percentile-ranked
    against its own trailing history. A FALLING ratio (long bonds
    underperforming short bonds) indicates rate stress -- so we
    invert the percentile rank (1 - rank) to keep the convention
    consistent with the other dials: higher reading = more stress.
    """
    if "TLT" not in px.columns or "SHY" not in px.columns:
        return None

    tlt = px.loc[:date, "TLT"].dropna()
    shy = px.loc[:date, "SHY"].dropna()
    if len(tlt) < 120 or len(shy) < 120:
        return None

    common = tlt.index.intersection(shy.index)
    ratio = (tlt.loc[common] / shy.loc[common]).dropna()
    hist = ratio.iloc[-lookback:] if len(ratio) >= lookback else ratio
    if len(hist) < 10:
        return None

    current = float(ratio.iloc[-1])
    # Falling ratio = rate stress, so invert: low percentile rank
    # (ratio is near the bottom of its range) = high stress reading
    reading = 1.0 - float((hist < current).mean())
    return reading


def validate_signal_separation(px, verbose=True):
    """
    Real stressed-vs-calm validation. Rate stress is different in
    CHARACTER from vol/currency shocks -- slow and grinding (2022)
    rather than sudden panics -- so the test periods are chosen
    to match that character specifically.
    """
    STRESSED_PERIODS = [
        ("2022-01-01", "2022-10-31", "2022 rate-driven grind"),
        ("2013-05-01", "2013-09-30", "Taper Tantrum -- also a real rate event"),
    ]
    CALM_PERIODS = [
        ("2005-01-01", "2005-12-31", "Calm mid-2000s"),
        ("2017-01-01", "2017-12-31", "Quiet bull market"),
        ("2012-01-01", "2012-12-31", "Calm rate environment"),
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


def compute_action_signal(current_reading, tlt_absolute_declining=None,
                          absolute_bar=0.615):
    """
    Same proven template PLUS the direction-confirmation fix
    learned from currency/EM, applied here from real testing:
    confirmed 13/52 false fires in 2017 caused by TLT genuinely
    RISING (real bond rally, $91.05->$95.01) while the ratio-based
    percentile still read as "unusual" and got treated as stress.
    Real rate stress means TLT DECLINING (rates rising hurts long
    bonds), not just "the ratio looks unusual" -- unusual can be
    in either direction, only one direction is actually stress.
    """
    is_unusual = current_reading >= absolute_bar
    if is_unusual and tlt_absolute_declining is False:
        # Ratio looks stressed but TLT is genuinely rising --
        # this is a bond rally, not rate stress. Override.
        is_unusual = False
    return is_unusual


def simulate_action_layer(px, dates, verbose=True):
    """Same proven trailing-window persistence."""
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

        tlt_declining = None
        if "TLT" in px.columns:
            tlt = px.loc[:d, "TLT"].dropna()
            if len(tlt) >= 65:
                # FIXED after finding a second, subtler false-fire
                # cause: a simple "below 63 days ago" check can flip
                # either way during genuinely CHOPPY, non-trending
                # periods (confirmed: TLT bounced 91.92->91.15->
                # 93.46->89.98->91.05 in early 2017, no real trend
                # either direction). A tiny, ambiguous move
                # shouldn't count as "genuinely declining" -- require
                # a MEANINGFUL decline (>1%), not just any negative
                # sign, to filter out pure noise/chop.
                pct_change = (tlt.iloc[-1] / tlt.iloc[-63]) - 1
                tlt_declining = bool(pct_change < -0.01)

        is_unusual = compute_action_signal(
            reading, tlt_absolute_declining=tlt_declining)
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
