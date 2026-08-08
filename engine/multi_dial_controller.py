"""
Multi-dial combination controller -- the actual point of the
redesign. Each dial computes its own reading and action-engaged
state independently. This module reads those independent outputs
and applies each to its OWN exclusive lever -- no dial can ever
touch another's lever, so no TLT-style collision is possible by
construction, not by convention.

Levers (from the finalized design):
  CREDIT dial      -> overall equity/defensive split (existing
                       main dial, unchanged, not rebuilt here)
  VOLATILITY dial  -> rate-limiter speed multiplier
  CURRENCY/EM dial -> EEM/SCHF slice weight within equity sleeve
  RATE dial        -> TBF/duration sleeve weight
                       (NOT YET READY -- rate dial's action layer
                       incomplete, placeholder used here, real
                       integration pending its completion)
"""
import pandas as pd
import numpy as np

import dial_currency_em
import dial_volatility
# import dial_rate  -- NOT wired in yet, action layer incomplete


def compute_all_dial_states(px, date, currency_history, vol_history):
    """
    Compute the independent state of every ready dial at a single
    date. Returns a dict -- each dial's engaged/not-engaged status
    and raw reading, kept fully separate, nothing blended.

    currency_history / vol_history: the trailing window of recent
    unusual/not-unusual flags, threaded through by the caller
    across weeks (same pattern as size_positions_smoothed's
    previous_weights threading -- pure function of state passed
    in, not stored internally).
    """
    em_reading = dial_currency_em.compute_raw_reading(px, date)
    vol_reading = dial_volatility.compute_raw_reading(px, date)

    em_declining = None
    if "EEM" in px.columns:
        eem = px.loc[:date, "EEM"].dropna()
        if len(eem) >= 65:
            em_declining = bool(eem.iloc[-1] < eem.iloc[-63])

    em_unusual = False
    if em_reading is not None:
        em_unusual = dial_currency_em.compute_action_signal(
            currency_history, em_reading,
            eem_absolute_declining=em_declining)[0]

    vol_unusual = False
    if vol_reading is not None:
        vol_unusual = dial_volatility.compute_action_signal(vol_reading)

    return {
        "currency_em": {"reading": em_reading, "unusual": em_unusual},
        "volatility": {"reading": vol_reading, "unusual": vol_unusual},
        "rate": {"reading": None, "unusual": False,
                "note": "dial not yet complete, always inactive"},
    }


def apply_levers(base_equity_target, base_rate_limiter_step,
                 base_eem_weight, dial_states,
                 vol_engaged_window_frac, em_engaged_window_frac):
    """
    Apply each dial's OWN exclusive lever, independently. This is
    the actual multi-move behavior discussed and agreed on this
    session: zero, one, two, or three levers can move in a single
    week, entirely independently, because none of them share a
    resource.

    base_equity_target: whatever the credit dial / main system has
      already decided (UNCHANGED by this function -- credit dial
      owns this lever exclusively, this function never touches it)
    base_rate_limiter_step: the normal per-week move size
    base_eem_weight: the EEM/SCHF weight the equity-sleeve scorer
      would otherwise assign

    Returns the adjusted rate-limiter step and EEM weight -- NOT
    equity_target, which passes through completely untouched,
    proving by construction that the credit dial's lever was never
    touched by anything else.
    """
    # VOLATILITY lever: speed multiplier only, never touches WHAT
    # is held, only HOW FAST toward the credit dial's own target
    if dial_states["volatility"]["unusual"]:
        adjusted_step = base_rate_limiter_step * 1.5  # move 50% faster
    else:
        adjusted_step = base_rate_limiter_step

    # CURRENCY/EM lever: EEM/SCHF slice weight only, never touches
    # overall equity/defensive split
    if dial_states["currency_em"]["unusual"]:
        adjusted_eem_weight = base_eem_weight * 0.5  # trim EM slice by half
    else:
        adjusted_eem_weight = base_eem_weight

    return {
        "equity_target": base_equity_target,  # UNCHANGED, credit dial's lever only
        "rate_limiter_step": adjusted_step,
        "eem_weight": adjusted_eem_weight,
        "moves_made": sum([
            dial_states["volatility"]["unusual"],
            dial_states["currency_em"]["unusual"],
        ]),
    }


if __name__ == "__main__":
    import os
    DATA_DIR = os.path.expanduser("~/tradingbot/engine/histdata")
    px = pd.read_parquet(os.path.join(DATA_DIR, "bt_prices.parquet"))
    px.index = pd.to_datetime(px.index).tz_localize(None)

    # Quick sanity check: walk a real window, show which levers
    # move independently, confirming zero/one/two-move weeks all
    # occur naturally rather than being forced
    test_dates = pd.date_range("2013-01-01", "2013-12-31", freq="W-FRI")

    em_hist = []
    for d in test_dates:
        states = compute_all_dial_states(px, d, em_hist, None)
        if states["currency_em"]["reading"] is not None:
            em_hist.append(states["currency_em"]["reading"])

        moves = []
        if states["currency_em"]["unusual"]:
            moves.append("EM-slice-trim")
        if states["volatility"]["unusual"]:
            moves.append("speed-up")

        move_str = ", ".join(moves) if moves else "no moves"
        print(f"  {d.date()}: {move_str}")
