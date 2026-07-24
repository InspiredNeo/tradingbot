"""
Page components for the Dash Market Terminal.
"""
import os
import sys
from datetime import datetime, timezone

from dash import dcc, html
import dash_bootstrap_components as dbc
import yfinance as yf
import plotly.graph_objects as go

sys.path.append(os.path.expanduser("~/tradingbot/dashboard"))

COLORS = {
    "bg": "#080c12",
    "panel": "#0d1219",
    "panel2": "#11161f",
    "border": "#1a2130",
    "border2": "#2d3748",
    "text": "#e2e8f0",
    "text2": "#94a3b8",
    "text3": "#64748b",
    "green": "#4ade80",
    "red": "#f87171",
    "blue": "#4b8bf5",
    "amber": "#f59e0b",
}
FONT_MONO = "JetBrains Mono, monospace"

SENTIMENT_COLORS = {
    "Bullish": "#12b76a",
    "Somewhat-Bullish": "#4caf50",
    "Neutral": "#8a8f98",
    "Somewhat-Bearish": "#f59e0b",
    "Bearish": "#ef4444",
}


def card_style(border_color=None):
    return {
        "background": COLORS["panel"],
        "border": f"1px solid {border_color or COLORS['border']}",
        "borderRadius": "10px",
        "padding": "14px 18px",
        "marginBottom": "10px",
    }


def time_ago(published):
    try:
        dt = datetime.strptime(published, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    except Exception:
        return ""
    mins = int((datetime.now(timezone.utc) - dt).total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    if mins < 60 * 24:
        return f"{mins // 60}h ago"
    return f"{mins // (60 * 24)}d ago"


def sentiment_pill(label):
    color = SENTIMENT_COLORS.get(label, "#8a8f98")
    return html.Span(label.upper(), style={
        "background": color, "color": "#fff", "fontSize": "10px",
        "fontWeight": "700", "padding": "3px 9px", "borderRadius": "999px",
        "letterSpacing": ".3px",
    })


# ---------- News page ----------
def news_article_card(article, idx):
    label = article.get("overall_sentiment_label", "Neutral")
    img = article.get("banner_image", "")
    return html.Div([
        html.Img(src=img, style={
            "width": "100%", "height": "150px", "objectFit": "cover",
            "objectPosition": "top", "borderRadius": "8px 8px 0 0",
        }) if img else None,
        html.Div([
            sentiment_pill(label),
            html.Div(article.get("title", ""), style={
                "color": COLORS["text"], "fontWeight": "700", "fontSize": "14px",
                "margin": "8px 0 6px", "lineHeight": "1.3",
            }),
            html.Div(f'{article.get("source", "")} · {time_ago(article.get("time_published", ""))}',
                     style={"color": COLORS["text3"], "fontSize": "12px"}),
        ], style={"padding": "12px 14px"}),
    ],
    id={"type": "news-card", "index": idx},
    n_clicks=0,
    style={
        "background": COLORS["panel"],
        "border": f"1px solid {COLORS['border']}",
        "borderRadius": "10px",
        "overflow": "hidden",
        "cursor": "pointer",
        "transition": "border-color .15s ease",
    })


def news_grid(feed):
    """Hero + grid of clickable article cards."""
    def good_image(a):
        img = a.get("banner_image", "")
        if not img:
            return False
        bad = ["logo", "icon", "avatar", "placeholder", "default", "blank"]
        return not any(b in img.lower() for b in bad)

    with_img = [a for a in feed if good_image(a)]
    if not with_img:
        return html.Div("No articles with images available right now.",
                        style={"color": COLORS["text2"]})

    hero = with_img[0]
    label = hero.get("overall_sentiment_label", "Neutral")
    hero_card = html.Div([
        html.Div([
            html.Img(src=hero.get("banner_image", ""), style={
                "width": "100%", "height": "340px", "objectFit": "cover",
                "objectPosition": "top", "display": "block",
            }),
            html.Div([
                sentiment_pill(label),
                html.H2(hero.get("title", ""), style={
                    "color": "#fff", "fontSize": "26px", "fontWeight": "800",
                    "margin": "10px 0 4px", "lineHeight": "1.2",
                }),
                html.Div(f'{hero.get("source", "")} · {time_ago(hero.get("time_published", ""))}',
                         style={"color": "#d1d5db", "fontSize": "13px"}),
            ], style={
                "position": "absolute", "left": 0, "right": 0, "bottom": 0,
                "padding": "26px",
                "background": "linear-gradient(to top, rgba(0,0,0,.85) 10%, rgba(0,0,0,.35) 55%, rgba(0,0,0,0) 100%)",
            }),
        ], style={"position": "relative", "borderRadius": "14px", "overflow": "hidden"}),
    ],
    id={"type": "news-card", "index": 0},
    n_clicks=0,
    style={"cursor": "pointer", "marginBottom": "22px"})

    rest = with_img[1:20]
    cards = [news_article_card(a, i + 1) for i, a in enumerate(rest)]
    grid = html.Div(cards, style={
        "display": "grid",
        "gridTemplateColumns": "repeat(3, 1fr)",
        "gap": "18px",
    })

    return html.Div([hero_card, grid])


def article_detail(article, insight_text):
    label = article.get("overall_sentiment_label", "Neutral")
    return html.Div([
        dbc.Button("← Back to News", id="news-back-btn", color="secondary",
                   size="sm", className="mb-3"),
        html.Img(src=article.get("banner_image", ""), style={
            "width": "100%", "maxHeight": "400px", "objectFit": "cover",
            "borderRadius": "12px", "marginBottom": "16px",
        }) if article.get("banner_image") else None,
        sentiment_pill(label),
        html.H2(article.get("title", ""), style={"color": COLORS["text"], "margin": "12px 0"}),
        html.Div(f'{article.get("source", "")} · {time_ago(article.get("time_published", ""))}',
                 style={"color": COLORS["text3"], "fontSize": "13px", "marginBottom": "12px"}),
        html.P(article.get("summary", ""), style={"color": COLORS["text2"]}),
        html.A("Read full article →", href=article.get("url", "#"), target="_blank",
               style={"color": COLORS["blue"]}),
        html.Hr(style={"borderColor": COLORS["border"]}),
        html.Div(dcc.Markdown(insight_text), style={
            "background": "#0d1a13", "border": "1px solid #1a3d2a",
            "borderLeft": f"3px solid {COLORS['green']}", "borderRadius": "8px",
            "padding": "16px 20px", "color": "#d1d5db",
        }) if insight_text else html.Div("Generating AI analysis...",
                                          style={"color": COLORS["text2"]}),
    ])


# ---------- Ticker detail ----------
def ticker_detail_page(sym, period="1y"):
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period=period)
        info = ticker.info
    except Exception:
        hist, info = None, {}

    name = info.get("longName", sym)
    price = info.get("currentPrice") or info.get("regularMarketPrice", 0) or 0
    prev_close = info.get("previousClose", 0) or 0
    change = price - prev_close if price and prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0
    color = COLORS["green"] if change >= 0 else COLORS["red"]
    arrow = "▲" if change >= 0 else "▼"

    header = html.Div([
        html.Div(name, style={"color": COLORS["text3"], "fontSize": "12px", "fontWeight": "600"}),
        html.Div([
            html.Span(sym, style={"color": COLORS["text"], "fontSize": "34px", "fontWeight": "800",
                                  "fontFamily": FONT_MONO, "marginRight": "16px"}),
            html.Span(f"${price:,.2f}", style={"color": COLORS["text"], "fontSize": "26px",
                                                "fontWeight": "700", "marginRight": "16px"}),
            html.Span(f"{arrow} {change:+.2f} ({change_pct:+.2f}%)",
                      style={"color": color, "fontSize": "17px", "fontWeight": "700"}),
        ], style={"display": "flex", "alignItems": "baseline", "marginTop": "6px"}),
    ], style=card_style())

    # Period buttons
    periods = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "5Y"]
    period_map = {"1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo",
                  "6M": "6mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y"}
    current_label = next((k for k, v in period_map.items() if v == period), "1Y")
    period_btns = html.Div([
        dbc.Button(p, id={"type": "period-btn", "index": p}, size="sm",
                   color="primary" if p == current_label else "secondary",
                   outline=(p != current_label),
                   className="me-1")
        for p in periods
    ], className="mb-3")

    # Chart
    chart = html.Div("Chart data unavailable.", style={"color": COLORS["text2"]})
    if hist is not None and not hist.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hist.index, y=hist["Close"], mode="lines",
            line=dict(color=COLORS["blue"], width=2),
            fill="tozeroy", fillcolor="rgba(75,139,245,0.1)",
        ))
        fig.update_layout(
            paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
            font=dict(color=COLORS["text2"]),
            xaxis=dict(gridcolor=COLORS["border"]),
            yaxis=dict(gridcolor=COLORS["border"]),
            margin=dict(l=0, r=0, t=10, b=0), height=350,
        )
        chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

    # Ratios
    ratios = [
        ("P/E Ratio", info.get("trailingPE"), None),
        ("Forward P/E", info.get("forwardPE"), None),
        ("P/B Ratio", info.get("priceToBook"), None),
        ("EV/EBITDA", info.get("enterpriseToEbitda"), None),
        ("Profit Margin", info.get("profitMargins"), "pct"),
        ("Revenue Growth", info.get("revenueGrowth"), "pct"),
        ("Debt/Equity", info.get("debtToEquity"), None),
        ("ROE", info.get("returnOnEquity"), "pct"),
        ("Market Cap", info.get("marketCap"), "cap"),
        ("52W High", info.get("fiftyTwoWeekHigh"), None),
        ("52W Low", info.get("fiftyTwoWeekLow"), None),
        ("Div Yield", info.get("dividendYield"), "pct"),
    ]
    ratio_cards = []
    for label, val, fmt in ratios:
        if val is None:
            display = "N/A"
        elif fmt == "pct":
            display = f"{val*100:.2f}%"
        elif fmt == "cap":
            display = f"${val/1e9:.2f}B" if val > 1e9 else f"${val/1e6:.0f}M"
        else:
            display = f"{val:.2f}"
        ratio_cards.append(html.Div([
            html.Div(label, style={"color": COLORS["text3"], "fontSize": "11px", "fontWeight": "600"}),
            html.Div(display, style={"color": COLORS["text"], "fontSize": "17px",
                                     "fontWeight": "700", "marginTop": "4px"}),
        ], style=card_style()))

    ratios_grid = html.Div(ratio_cards, style={
        "display": "grid", "gridTemplateColumns": "repeat(4, 1fr)", "gap": "10px",
    })

    return html.Div([
        dbc.Button("← Back", id="ticker-back-btn", color="secondary", size="sm", className="mb-3"),
        header,
        period_btns,
        chart,
        html.Div("KEY RATIOS", style={"color": COLORS["text3"], "fontSize": "11px",
                                       "fontWeight": "600", "letterSpacing": "0.5px",
                                       "margin": "20px 0 12px"}),
        ratios_grid,
        html.Div(id="ticker-ai-analysis", style={"marginTop": "20px"}),
    ])
