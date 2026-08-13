"""
Real, systematic test of different momentum/liquidity weightings,
using the same two-window discipline that caught real overfitting
in the target_count testing -- never trust a single-window result.
"""
from backtest_universe_selection import run_selection_backtest


def evaluate(label, start, end, years, **kwargs):
    df = run_selection_backtest(start=start, end=end, verbose=False, **kwargs)
    if len(df) == 0:
        print(f"{label}: no data")
        return None

    final_val = df["value"].iloc[-1]
    total_return = (final_val - 10000) / 10000
    df["returns"] = df["value"].pct_change()
    vol = df["returns"].std() * (52 ** 0.5)
    running_max = df["value"].cummax()
    drawdown = (df["value"] - running_max) / running_max
    max_dd = drawdown.min()
    ann_return = (1 + total_return) ** (1 / years) - 1
    ratio = ann_return / vol if vol > 0 else 0

    print(f"{label:<25} ann={ann_return:>6.1%}  vol={vol:>6.1%}  "
          f"DD={max_dd:>7.1%}  ratio={ratio:.2f}")
    return ratio


if __name__ == "__main__":
    # Real, honest weighting variations to test, using the
    # currently most-robust target_count (15) from prior testing
    configs = [
        ("heavy momentum (0.6/0.1)", 0.6, 0.1),
        ("baseline (0.4/0.2)", 0.4, 0.2),
        ("balanced (0.3/0.3)", 0.3, 0.3),
        ("heavy liquidity (0.1/0.5)", 0.1, 0.5),
    ]

    print("REAL, IN-SAMPLE window: 2020-2026")
    print("-" * 90)
    for label, mw, lw in configs:
        evaluate(label, "2020-01-01", None, 6.5, target_count=15,
                 momentum_weight=mw, liquidity_weight=lw)

    print()
    print("REAL, OUT-OF-SAMPLE window: 2015-2020")
    print("-" * 90)
    for label, mw, lw in configs:
        evaluate(label, "2015-01-01", "2020-01-01", 5.0, target_count=15,
                 momentum_weight=mw, liquidity_weight=lw)
