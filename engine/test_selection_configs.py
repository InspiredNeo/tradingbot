"""
Real, systematic comparison across multiple universe-selection
configurations, testing whether further concentration or different
weightings produce genuine, honest improvement -- following up on
the real finding that 15-asset outperformed 25-asset on a
risk-adjusted basis, but neither yet beat blind VTI.
"""
from backtest_universe_selection import run_selection_backtest
import pandas as pd


def evaluate_config(label, **kwargs):
    df = run_selection_backtest(start="2020-01-01", verbose=False, **kwargs)

    if len(df) == 0:
        return {"label": label, "error": "no data"}

    final_val = df["value"].iloc[-1]
    total_return = (final_val - 10000) / 10000

    df["returns"] = df["value"].pct_change()
    vol = df["returns"].std() * (52 ** 0.5)

    running_max = df["value"].cummax()
    drawdown = (df["value"] - running_max) / running_max
    max_dd = drawdown.min()

    years = 6.5
    ann_return = (1 + total_return) ** (1 / years) - 1
    ratio = ann_return / vol if vol > 0 else 0

    result = {
        "label": label,
        "total_return": total_return,
        "ann_return": ann_return,
        "vol": vol,
        "max_dd": max_dd,
        "ratio": ratio,
    }
    print(f"{label:<20} return={total_return:>7.1%}  ann={ann_return:>6.1%}  "
          f"vol={vol:>6.1%}  DD={max_dd:>7.1%}  ratio={ratio:.2f}")
    return result


if __name__ == "__main__":
    print("Real, systematic configuration comparison (2020-2026):")
    print("VTI benchmark: ann=14.9%, vol=19.7%, DD=-35.0%, ratio=0.76")
    print("-" * 90)

    results = []
    results.append(evaluate_config("10-asset", target_count=10))
    results.append(evaluate_config("12-asset", target_count=12))
    results.append(evaluate_config("15-asset (baseline)", target_count=15))
    results.append(evaluate_config("18-asset", target_count=18))
    results.append(evaluate_config("20-asset", target_count=20))
