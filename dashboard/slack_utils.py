"""
Slack notification utilities for Market Terminal.
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))

WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def send_slack(message, blocks=None):
    """Send a plain or rich message to Slack."""
    try:
        payload = {"text": message}
        if blocks:
            payload["blocks"] = blocks
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def send_alert_triggered(symbol, condition, target, current_price):
    """Send a price alert notification."""
    arrow = "📈" if condition == "above" else "📉"
    color = "good" if condition == "above" else "danger"
    send_slack(
        f"{arrow} *Price Alert Triggered*",
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{arrow} Price Alert — {symbol}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Ticker:*\n{symbol}"},
                    {"type": "mrkdwn", "text": f"*Condition:*\n{condition.upper()} ${target:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Current Price:*\n${current_price:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M ET')}"},
                ]
            }
        ]
    )


def send_hard_sell(positions_sold, total_value, reasons):
    """Send hard sell notification and lock message."""
    positions_text = "\n".join(
        f"• {sym}: {shares} shares @ ${price:.2f} = ${shares*price:,.2f}"
        for sym, shares, price in positions_sold
    )
    reasons_text = "\n".join(f"• {r}" for r in reasons)
    send_slack(
        "🚨 HARD SELL EXECUTED — Bot Locked",
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 HARD SELL EXECUTED"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn",
                         "text": "*The bot has executed a hard sell and is now LOCKED. "
                                 "Manual authorization required to reinvest.*"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Positions Sold:*\n{positions_text}"},
                    {"type": "mrkdwn", "text": f"*Trigger Reasons:*\n{reasons_text}"},
                ]
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Liquidated:*\n${total_value:,.2f}"},
                    {"type": "mrkdwn",
                     "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M ET')}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn",
                         "text": "⚠️ *Action Required:* Open Market Terminal → Bot tab → "
                                 "click *Authorize Reinvestment* when ready to redeploy capital."}
            }
        ]
    )


def send_rebalance(old_alloc, new_alloc, model_used, regime):
    """Send rebalance notification."""
    changes = []
    all_syms = set(list(old_alloc.keys()) + list(new_alloc.keys()))
    for sym in all_syms:
        old_w = old_alloc.get(sym, 0)
        new_w = new_alloc.get(sym, 0)
        diff = new_w - old_w
        if abs(diff) > 0.5:
            arrow = "▲" if diff > 0 else "▼"
            changes.append(f"• {sym}: {old_w:.1f}% → {new_w:.1f}% ({arrow}{abs(diff):.1f}%)")

    if not changes:
        return

    send_slack(
        "🔄 Portfolio Rebalanced",
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🔄 Portfolio Rebalanced"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Model Used:*\n{model_used}"},
                    {"type": "mrkdwn", "text": f"*Market Regime:*\n{regime}"},
                    {"type": "mrkdwn", "text": f"*Changes:*\n" + "\n".join(changes)},
                    {"type": "mrkdwn",
                     "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M ET')}"},
                ]
            }
        ]
    )


def send_paper_milestone(paper_value, paper_budget, pnl_pct):
    """Send paper trading milestone notification."""
    emoji = "🎯" if pnl_pct >= 5 else "📊"
    send_slack(
        f"{emoji} Paper Trading Update",
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text",
                         "text": f"{emoji} Paper Trading {'Target Reached!' if pnl_pct >= 5 else 'Update'}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Portfolio Value:*\n${paper_value:,.2f}"},
                    {"type": "mrkdwn", "text": f"*Starting Budget:*\n${paper_budget:,.2f}"},
                    {"type": "mrkdwn", "text": f"*P&L:*\n{pnl_pct:+.2f}%"},
                    {"type": "mrkdwn",
                     "text": f"*Status:*\n{'🟢 Ready for Live Trading!' if pnl_pct >= 5 else '🟡 In Progress'}"},
                ]
            }
        ]
    )
