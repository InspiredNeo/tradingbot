"""
Real, systematic test of different turnover caps, using the same
risk-adjusted evaluation discipline that caught the real, honest
lesson that max_replacements=2 increased return but WORSENED
risk-adjusted performance. Testing a range of real, different caps
to see if there's a genuine sweet spot, the same way target_count
testing found one earlier tonight.
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

    print(f"{label:<20} ann={ann_return:>6.1%}  vol={vol:>6.1%}  "
          f"DD={max_dd:>7.1%}  ratio={ratio:.2f}")
    return ratio


if __name__ == "__main__":
    print("REAL, IN-SAMPLE window: 2020-2026")
    print("VTI benchmark: ratio=0.76")
    print("-" * 90)
    for cap in [1, 2, 3, 4, 5, None]:
        label = f"cap={cap}" if cap else "uncapped"
        evaluate(label, "2020-01-01", None, 6.5, target_count=15,
                 momentum_weight=0.3, liquidity_weight=0.3, max_replacements=cap)
