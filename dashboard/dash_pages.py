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
    periods = ["1D", "1W", "1M", "3M", "6M", "YTD", "5Y", "MAX"]
    period_map = {"1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo",
                  "6M": "6mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y", "MAX": "max"}
    current_label = next((k for k, v in period_map.items() if v == period), "1Y")
    period_btns = html.Div([
        dbc.Button(p, id={"type": "period-btn", "index": p, "sym": sym}, size="sm",
                   color="primary" if p == current_label else "secondary",
                   outline=(p != current_label),
                   className="me-1")
        for p in periods
    ], className="mb-3")

    # Chart - use stable ID so period changes only update the graph
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
        chart = dcc.Graph(figure=fig, id="ticker-chart", config={"displayModeBar": False})
    else:
        chart = html.Div("Chart data unavailable.", id="ticker-chart",
                        style={"color": COLORS["text2"]})

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


# ---------- Market Snapshot ----------
def get_snapshot():
    symbols = {
        "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "VIX": "^VIX",
        "Gold": "GC=F", "Oil": "CL=F", "10Y Yield": "^TNX",
    }
    results = {}
    try:
        data = yf.download(list(symbols.values()), period="2d", progress=False, group_by="ticker")
        for label, sym in symbols.items():
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    pct = ((curr - prev) / prev) * 100
                    results[label] = (curr, pct)
            except Exception:
                continue
    except Exception:
        pass
    return results


SNAPSHOT_TICKERS = {
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "VIX": "^VIX",
    "Gold": "GC=F", "Oil": "CL=F", "10Y Yield": "^TNX",
}

def snapshot_bar():
    snapshot = get_snapshot()
    if not snapshot:
        return html.Div()
    tiles = []
    for label, (price, pct) in snapshot.items():
        color = COLORS["green"] if pct >= 0 else COLORS["red"]
        arrow = "▲" if pct >= 0 else "▼"
        if label in ["VIX", "10Y Yield"]:
            price_str = f"{price:.2f}"
        elif price > 1000:
            price_str = f"{price:,.0f}"
        else:
            price_str = f"{price:.2f}"
        tiles.append(html.Div([
            html.Div(label, style={"color": COLORS["text3"], "fontSize": "11px",
                                   "fontWeight": "600", "letterSpacing": "0.5px",
                                   "fontFamily": FONT_MONO}),
            html.Div(price_str, style={"color": COLORS["text"], "fontSize": "18px",
                                       "fontWeight": "700", "margin": "4px 0 2px",
                                       "fontFamily": FONT_MONO}),
            html.Div(f"{arrow} {pct:+.2f}%", style={"color": color, "fontSize": "12px",
                                                     "fontWeight": "700"}),
        ],
        id={"type": "snapshot-tile", "sym": SNAPSHOT_TICKERS.get(label, label)},
        n_clicks=0,
        style={
            "cursor": "pointer",
            "background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
            "borderRadius": "10px", "padding": "12px 16px", "textAlign": "center",
            "flex": "1",
        }))
    return html.Div(tiles, style={"display": "flex", "gap": "12px", "marginBottom": "16px"})


def sentiment_gauge(feed):
    labels = [a.get("overall_sentiment_label", "Neutral") for a in feed]
    bullish = sum(1 for l in labels if "Bullish" in l)
    bearish = sum(1 for l in labels if "Bearish" in l)
    total = len(labels)
    bull_pct = int((bullish / total) * 100) if total else 0
    bear_pct = int((bearish / total) * 100) if total else 0
    neu_pct = 100 - bull_pct - bear_pct

    if bull_pct > 50:
        mood, mood_color = "Bullish", COLORS["green"]
    elif bear_pct > 50:
        mood, mood_color = "Bearish", COLORS["red"]
    elif bull_pct > bear_pct:
        mood, mood_color = "Leaning Bullish", "#86efac"
    elif bear_pct > bull_pct:
        mood, mood_color = "Leaning Bearish", "#fca5a5"
    else:
        mood, mood_color = "Neutral", COLORS["text2"]

    return html.Div([
        html.Div([
            html.Div("MARKET SENTIMENT", style={"color": COLORS["text3"], "fontSize": "11px",
                                                 "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(f"● {mood}", style={"color": mood_color, "fontSize": "20px",
                                          "fontWeight": "800", "marginTop": "2px"}),
        ]),
        html.Div([
            html.Div(style={"width": f"{bull_pct}%", "background": COLORS["green"], "height": "100%"}),
            html.Div(style={"width": f"{neu_pct}%", "background": "#475569", "height": "100%"}),
            html.Div(style={"width": f"{bear_pct}%", "background": COLORS["red"], "height": "100%"}),
        ], style={"flex": "1", "background": COLORS["border"], "borderRadius": "999px",
                  "height": "8px", "overflow": "hidden", "display": "flex", "margin": "0 20px"}),
        html.Div([
            html.Span(f"▲ {bull_pct}%  ", style={"color": COLORS["green"]}),
            html.Span(f"● {neu_pct}%  ", style={"color": COLORS["text2"]}),
            html.Span(f"▼ {bear_pct}%", style={"color": COLORS["red"]}),
        ], style={"fontSize": "12px", "fontFamily": FONT_MONO}),
    ], style={
        "background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
        "borderRadius": "10px", "padding": "14px 20px", "marginBottom": "20px",
        "display": "flex", "alignItems": "center",
    })


# ---------- Earnings ----------
def get_earnings():
    import requests
    from datetime import date, timedelta
    try:
        key = os.getenv("FINNHUB_API_KEY")
        today = date.today()
        to = today + timedelta(days=7)
        resp = requests.get("https://finnhub.io/api/v1/calendar/earnings",
                            params={"from": today.strftime("%Y-%m-%d"),
                                    "to": to.strftime("%Y-%m-%d"), "token": key}, timeout=15)
        return resp.json().get("earningsCalendar", [])
    except Exception:
        return []


def earnings_tab():
    earnings = [e for e in get_earnings() if e.get("epsEstimate") is not None]
    priority = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "SPY", "QQQ"]
    earnings.sort(key=lambda x: (x.get("date", ""), 0 if x.get("symbol") in priority else 1))
    if not earnings:
        return html.Div("No earnings data available.", style={"color": COLORS["text2"]})

    rows = [html.Div("Upcoming earnings for the next 7 days. BMO = Before Market Open · AMC = After Market Close",
                     style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"})]
    current_date = None
    for e in earnings[:50]:
        date_str = e.get("date", "")
        if date_str != current_date:
            current_date = date_str
            rows.append(html.Div(f"📅 {date_str}", style={
                "color": COLORS["blue"], "fontSize": "13px", "fontWeight": "700",
                "margin": "16px 0 8px", "paddingBottom": "6px",
                "borderBottom": f"1px solid {COLORS['border']}"}))
        sym = e.get("symbol", "")
        hour = e.get("hour", "")
        timing = "🌅 BMO" if hour == "bmo" else "🌆 AMC" if hour == "amc" else "⏰ TBD"
        eps_est = e.get("epsEstimate")
        eps_act = e.get("epsActual")
        rev_est = e.get("revenueEstimate")
        eps_str = f"${eps_est:.2f}" if eps_est is not None else "N/A"
        rev_str = f"${rev_est/1e9:.2f}B" if rev_est and rev_est > 1e9 else \
                  f"${rev_est/1e6:.0f}M" if rev_est and rev_est > 1e6 else "N/A"
        if eps_act is not None and eps_est:
            beat = eps_act >= eps_est
            result = html.Span(f'{"BEAT" if beat else "MISS"} ${eps_act:.2f}',
                               style={"color": COLORS["green"] if beat else COLORS["red"],
                                      "fontWeight": "700"})
        else:
            result = html.Span("Pending", style={"color": COLORS["text3"]})
        is_priority = sym in priority
        rows.append(html.Div([
            html.Span(sym, style={"color": COLORS["text"], "fontWeight": "700",
                                  "fontSize": "15px", "fontFamily": FONT_MONO,
                                  "minWidth": "70px"}),
            html.Span(timing, style={"color": COLORS["text3"], "fontSize": "12px",
                                     "minWidth": "70px"}),
            html.Span([
                html.Span("EPS Est: ", style={"color": COLORS["text2"], "fontSize": "12px"}),
                html.Span(eps_str, style={"color": COLORS["text"], "fontSize": "12px",
                                          "fontWeight": "600"}),
                html.Span("  |  Rev Est: ", style={"color": COLORS["text2"], "fontSize": "12px"}),
                html.Span(rev_str, style={"color": COLORS["text"], "fontSize": "12px",
                                          "fontWeight": "600"}),
            ], style={"flex": "1"}),
            result,
        ], style={
            "background": COLORS["panel"],
            "border": f"1px solid {COLORS['blue'] if is_priority else COLORS['border']}",
            "borderRadius": "8px", "padding": "12px 16px", "marginBottom": "8px",
            "display": "flex", "alignItems": "center", "gap": "16px"}))
    return html.Div(rows)


# ---------- Insider Trading ----------
def get_insider_trades():
    import requests
    try:
        key = os.getenv("FINNHUB_API_KEY")
        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "SPY", "QQQ", "BND"]
        all_trades = []
        for sym in symbols:
            try:
                resp = requests.get("https://finnhub.io/api/v1/stock/insider-transactions",
                                    params={"symbol": sym, "token": key}, timeout=10)
                for t in resp.json().get("data", [])[:5]:
                    t["symbol"] = sym
                    all_trades.append(t)
            except Exception:
                continue
        all_trades.sort(key=lambda x: x.get("filingDate", ""), reverse=True)
        trades = [t for t in all_trades
                  if t.get("transactionCode") in ["B", "S", "P"]
                  and not t.get("isDerivative", False)]
        return trades[:40]
    except Exception:
        return []


def insider_tab():
    trades = get_insider_trades()
    if not trades:
        return html.Div("No insider trading data available.", style={"color": COLORS["text2"]})
    rows = [html.Div("Recent insider transactions. Click any trade for AI analysis.",
                     style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"})]
    current_sym = None
    for i, t in enumerate(trades):
        sym = t.get("symbol", "")
        name = t.get("name", "Unknown")
        shares = t.get("change", 0)
        price = t.get("transactionPrice", 0)
        date_str = t.get("transactionDate", "")
        value = abs(shares * price) if price else 0
        is_buy = shares > 0
        color = COLORS["green"] if is_buy else COLORS["red"]
        action = "BUY" if is_buy else "SELL"
        arrow = "▲" if is_buy else "▼"
        val_str = f"${value:,.0f}" if value > 0 else "N/A"
        price_str = f"${price:.2f}" if price else "N/A"
        if sym != current_sym:
            current_sym = sym
            rows.append(html.Div(sym, style={
                "color": COLORS["blue"], "fontSize": "13px", "fontWeight": "700",
                "margin": "16px 0 8px", "paddingBottom": "6px",
                "borderBottom": f"1px solid {COLORS['border']}"}))
        rows.append(html.Div([
            html.Div([
                html.Span(f"{arrow} {action}", style={"color": color, "fontWeight": "700",
                                                       "fontSize": "12px", "minWidth": "60px"}),
                html.Span(name, style={"color": COLORS["text"], "fontSize": "13px", "flex": "1"}),
                html.Span(f"{abs(shares):,} @ {price_str}", style={"color": COLORS["text2"],
                                                                     "fontSize": "12px"}),
                html.Span(val_str, style={"color": color, "fontSize": "12px",
                                          "fontWeight": "700"}),
                html.Span(date_str, style={"color": COLORS["text3"], "fontSize": "12px"}),
            ], style={"display": "flex", "alignItems": "center", "gap": "16px"}),
            html.Div(id={"type": "insider-insight", "index": i}),
        ],
        id={"type": "insider-trade", "index": i},
        n_clicks=0,
        style={
            "background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
            "borderLeft": f"3px solid {color}", "borderRadius": "8px",
            "padding": "10px 16px", "marginBottom": "6px", "cursor": "pointer"}))
    return html.Div(rows)


# ---------- SEC Filings ----------
def get_sec_filings():
    import requests
    try:
        key = os.getenv("FINNHUB_API_KEY")
        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"]
        all_filings = []
        for sym in symbols:
            try:
                resp = requests.get("https://finnhub.io/api/v1/stock/filings",
                                    params={"symbol": sym, "token": key}, timeout=10)
                filings = resp.json()
                if isinstance(filings, list):
                    for f in filings[:3]:
                        f["symbol"] = sym
                        all_filings.append(f)
            except Exception:
                continue
        all_filings.sort(key=lambda x: x.get("filedDate", ""), reverse=True)
        return all_filings[:30]
    except Exception:
        return []


def sec_tab():
    filings = get_sec_filings()
    if not filings:
        return html.Div("No SEC filings available.", style={"color": COLORS["text2"]})
    rows = [html.Div("Latest SEC filings for your watched tickers.",
                     style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"})]
    for f in filings:
        sym = f.get("symbol", "")
        form = f.get("form", "")
        filed = f.get("filedDate", "")
        desc = f.get("description", form)
        url = f.get("reportUrl") or f.get("filingUrl") or "#"
        form_color = COLORS["red"] if form in ["8-K", "SC 13G", "SC 13D"] else \
                     COLORS["blue"] if form in ["10-K", "10-Q"] else COLORS["text2"]
        rows.append(html.A([
            html.Span(sym, style={"color": COLORS["text"], "fontWeight": "700",
                                  "fontSize": "14px", "fontFamily": FONT_MONO,
                                  "minWidth": "60px"}),
            html.Span(form, style={"color": form_color, "fontSize": "12px",
                                   "fontWeight": "700", "background": f"{form_color}22",
                                   "padding": "2px 10px", "borderRadius": "4px",
                                   "minWidth": "50px", "textAlign": "center"}),
            html.Span(desc, style={"color": COLORS["text2"], "fontSize": "13px", "flex": "1"}),
            html.Span(filed, style={"color": COLORS["text3"], "fontSize": "12px"}),
        ], href=url, target="_blank", style={
            "background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
            "borderRadius": "8px", "padding": "12px 16px", "marginBottom": "8px",
            "display": "flex", "alignItems": "center", "gap": "16px",
            "textDecoration": "none"}))
    return html.Div(rows)


# ---------- Category tabs (Stocks/ETFs/World) ----------
sys.path.append(os.path.expanduser("~/tradingbot/engine"))


def category_content(category, articles, active_filter="All", summary_text=None):
    """Render a Stocks/ETFs/World tab with filters, summary, and articles."""
    if not articles:
        return html.Div("No articles available right now from any source.",
                        style={"color": COLORS["text2"]})

    bullish = sum(1 for a in articles if "Bullish" in a["sentiment_label"])
    bearish = sum(1 for a in articles if "Bearish" in a["sentiment_label"])
    neutral = len(articles) - bullish - bearish

    def filter_btn(label, count, filter_val, color):
        active = active_filter == filter_val
        return html.Div(
            f"{label}  {count}",
            id={"type": "cat-filter", "cat": category, "val": filter_val},
            n_clicks=0,
            style={
                "background": COLORS["panel2"] if active else COLORS["panel"],
                "border": f"1px solid {color if active else COLORS['border2']}",
                "borderRadius": "8px", "padding": "10px 16px", "flex": "1",
                "textAlign": "center", "cursor": "pointer",
                "color": color, "fontWeight": "700", "fontSize": "13px",
            })

    filters = html.Div([
        filter_btn("📊 ALL", len(articles), "All", COLORS["text"]),
        filter_btn("🟢 BULLISH", bullish, "Bullish", COLORS["green"]),
        filter_btn("🔴 BEARISH", bearish, "Bearish", COLORS["red"]),
        filter_btn("⚪ NEUTRAL", neutral, "Neutral", COLORS["text2"]),
    ], style={"display": "flex", "gap": "12px", "marginBottom": "16px"})

    summary_box = html.Div(dcc.Markdown(summary_text), style={
        "background": "#0d1a13", "border": "1px solid #1a3d2a",
        "borderLeft": f"3px solid {COLORS['green']}", "borderRadius": "8px",
        "padding": "16px 20px", "marginBottom": "20px", "color": "#d1d5db",
    }) if summary_text else html.Div("Generating market summary...",
                                      style={"color": COLORS["text2"], "marginBottom": "20px"})

    # Filter articles
    if active_filter == "Bullish":
        filtered = [a for a in articles if "Bullish" in a["sentiment_label"]]
    elif active_filter == "Bearish":
        filtered = [a for a in articles if "Bearish" in a["sentiment_label"]]
    elif active_filter == "Neutral":
        filtered = [a for a in articles
                    if "Bullish" not in a["sentiment_label"]
                    and "Bearish" not in a["sentiment_label"]]
    else:
        filtered = articles

    article_items = []
    for i, a in enumerate(filtered):
        s_label = a.get("sentiment_label", "Neutral")
        s_color = COLORS["green"] if "Bullish" in s_label else \
                  COLORS["red"] if "Bearish" in s_label else COLORS["text2"]
        article_items.append(
            dbc.AccordionItem([
                html.Div([
                    html.Span(a.get("source", ""), style={"color": COLORS["text3"],
                                                           "fontSize": "12px"}),
                    html.Span(f'  |  {a.get("data_source", "")}  |  ',
                              style={"color": COLORS["text3"], "fontSize": "12px"}),
                    html.Span(f'{s_label} ({a.get("sentiment_score", 0)})',
                              style={"color": s_color, "fontSize": "12px",
                                     "fontWeight": "600"}),
                ], style={"marginBottom": "10px"}),
                html.Div([
                    html.Img(src=a.get("banner_image", ""), style={
                        "width": "200px", "borderRadius": "8px", "marginRight": "16px",
                        "objectFit": "cover",
                    }) if a.get("banner_image") else None,
                    html.Div([
                        html.P(a.get("summary", ""), style={"color": COLORS["text2"],
                                                             "fontSize": "13px"}),
                        html.A("Read full article", href=a.get("url", "#"), target="_blank",
                               style={"color": COLORS["blue"], "fontSize": "13px"}),
                    ], style={"flex": "1"}),
                ], style={"display": "flex"}),
                html.Div(id={"type": "cat-article-insight", "cat": category, "index": i}),
            ], title=a.get("title", ""), item_id=f"{category}-{i}")
        )

    accordion = dbc.Accordion(article_items, start_collapsed=True, flush=True,
                              id={"type": "cat-accordion", "cat": category})

    return html.Div([
        filters,
        summary_box,
        html.Div("Headlines", style={"color": "#cbd5e1", "fontSize": "15px",
                                      "fontWeight": "600", "margin": "8px 0 4px"}),
        html.Div("Click an article to expand for full AI analysis.",
                 style={"color": COLORS["text3"], "fontSize": "12px",
                        "marginBottom": "16px"}),
        accordion,
    ])


# ---------- Browse tab ----------
BROWSE_STOCKS = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","BRK-B","JPM","V",
    "JNJ","WMT","PG","MA","HD","BAC","XOM","PFE","ABBV","KO",
    "PEP","AVGO","COST","MRK","CVX","TMO","ABT","CRM","ACN","MCD",
    "NFLX","ADBE","NKE","DHR","TXN","PM","NEE","ORCL","AMD","QCOM",
    "LIN","UPS","RTX","HON","AMGN","IBM","GS","CAT","SBUX","GE"
]
BROWSE_ETFS = [
    "SPY","QQQ","VTI","VOO","IWM","DIA","GLD","SLV","TLT","HYG",
    "VNQ","XLF","XLK","XLE","XLV","XLI","XLY","XLP","XLU","XLB",
    "ARKK","ARKG","ARKW","VGT","VHT","VFH","VDE","VPU","VIS","VAW",
    "BND","AGG","LQD","EMB","VCIT","VCSH","BSV","BNDX","MUB","VTEB"
]


def browse_ticker_card(sym, in_watchlist):
    border = COLORS["blue"] if in_watchlist else COLORS["border"]
    return html.Div([
        html.Div(sym, style={"color": COLORS["text"], "fontWeight": "700",
                             "fontSize": "14px", "fontFamily": FONT_MONO,
                             "textAlign": "center"}),
        html.Div("IN WATCHLIST" if in_watchlist else "", style={
            "color": COLORS["blue"], "fontSize": "9px", "textAlign": "center",
            "height": "12px"}),
        html.Div([
            html.Div("View", id={"type": "browse-view", "index": sym}, n_clicks=0,
                     style={"flex": "1", "textAlign": "center", "padding": "6px",
                            "background": COLORS["panel2"], "borderRadius": "6px",
                            "cursor": "pointer", "color": COLORS["text2"],
                            "fontSize": "12px"}),
            html.Div("✕ Remove" if in_watchlist else "+ Add",
                     id={"type": "browse-toggle", "index": sym}, n_clicks=0,
                     style={"flex": "1", "textAlign": "center", "padding": "6px",
                            "background": COLORS["panel2"], "borderRadius": "6px",
                            "cursor": "pointer",
                            "color": COLORS["red"] if in_watchlist else COLORS["green"],
                            "fontSize": "12px"}),
        ], style={"display": "flex", "gap": "6px", "marginTop": "8px"}),
    ], style={
        "background": COLORS["panel"], "border": f"1px solid {border}",
        "borderRadius": "8px", "padding": "12px 14px",
    })


def browse_tab_content(watchlist_symbols, search=""):
    search_upper = (search or "").strip().upper()

    def grid(symbols):
        cards = [browse_ticker_card(s, s in watchlist_symbols) for s in symbols]
        return html.Div(cards, style={
            "display": "grid", "gridTemplateColumns": "repeat(5, 1fr)", "gap": "12px"})

    if search_upper:
        matches = [s for s in BROWSE_STOCKS + BROWSE_ETFS if search_upper in s]
        if matches:
            return grid(matches)
        # Live lookup - try any valid ticker
        try:
            ticker_obj = yf.Ticker(search_upper)
            info = ticker_obj.info
            # Accept if we get any useful info back
            has_data = (info.get("regularMarketPrice") or 
                       info.get("currentPrice") or 
                       info.get("previousClose") or
                       info.get("symbol") or
                       info.get("shortName"))
            if has_data and info.get("symbol"):
                name = info.get("longName") or info.get("shortName") or search_upper
                return html.Div([
                    html.Div(f"Found: {search_upper} — {name}",
                             style={"color": COLORS["text"], "marginBottom": "12px",
                                    "fontWeight": "600"}),
                    html.Div(browse_ticker_card(search_upper, search_upper in watchlist_symbols),
                             style={"maxWidth": "220px"}),
                ])
        except Exception as e:
            pass
        return html.Div(f"No results found for '{search}'. Try the exact ticker symbol (e.g. AAPL, BTC-USD, EURUSD=X)",
                       style={"color": COLORS["text2"]})

    return html.Div([
        html.Div("STOCKS", style={"color": COLORS["text3"], "fontSize": "11px",
                                   "fontWeight": "600", "letterSpacing": "0.5px",
                                   "margin": "10px 0"}),
        grid(BROWSE_STOCKS),
        html.Div("ETFS", style={"color": COLORS["text3"], "fontSize": "11px",
                                 "fontWeight": "600", "letterSpacing": "0.5px",
                                 "margin": "20px 0 10px"}),
        grid(BROWSE_ETFS),
    ])


# ---------- Portfolio ----------
import json

PORTFOLIO_FILE = os.path.expanduser("~/tradingbot/config/portfolio.json")


def load_portfolio():
    try:
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []  # list of {"symbol": "VTI", "shares": 10, "cost_basis": 250.00}


def save_portfolio(holdings):
    try:
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(holdings, f)
    except Exception:
        pass


def portfolio_tab():
    holdings = load_portfolio()

    # Add holding form
    add_form = html.Div([
        html.Div("ADD HOLDING", style={"color": COLORS["text3"], "fontSize": "11px",
                                        "fontWeight": "600", "letterSpacing": "0.5px",
                                        "marginBottom": "10px"}),
        html.Div([
            dbc.Input(id="pf-symbol", placeholder="Ticker (e.g. VTI)",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Input(id="pf-shares", placeholder="Shares", type="number",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Input(id="pf-cost", placeholder="Cost/share", type="number",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Button("Add", id="pf-add-btn", color="primary", size="sm"),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "24px"}),
    ])

    if not holdings:
        return html.Div([add_form,
                         html.Div("No holdings yet. Add your positions above to track them.",
                                  style={"color": COLORS["text2"]})])

    # Fetch current prices
    symbols = [h["symbol"] for h in holdings]
    prices = {}
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if not hist.empty:
                prices[sym] = float(hist["Close"].dropna().iloc[-1])
            else:
                prices[sym] = 0
        except Exception:
            prices[sym] = 0

    # Calculate totals
    total_value = 0
    total_cost = 0
    rows_data = []
    for h in holdings:
        sym = h["symbol"]
        shares = h.get("shares", 0)
        cost = h.get("cost_basis", 0)
        price = prices.get(sym, 0)
        value = shares * price
        cost_total = shares * cost
        gain = value - cost_total
        gain_pct = (gain / cost_total * 100) if cost_total else 0
        total_value += value
        total_cost += cost_total
        rows_data.append((sym, shares, cost, price, value, gain, gain_pct))

    total_gain = total_value - total_cost
    total_gain_pct = (total_gain / total_cost * 100) if total_cost else 0
    gain_color = COLORS["green"] if total_gain >= 0 else COLORS["red"]

    # Summary cards
    summary = html.Div([
        html.Div([
            html.Div("TOTAL VALUE", style={"color": COLORS["text3"], "fontSize": "11px", "fontWeight": "600"}),
            html.Div(f"${total_value:,.2f}", style={"color": COLORS["text"], "fontSize": "24px",
                                                     "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px", "flex": "1"}),
        html.Div([
            html.Div("TOTAL COST", style={"color": COLORS["text3"], "fontSize": "11px", "fontWeight": "600"}),
            html.Div(f"${total_cost:,.2f}", style={"color": COLORS["text"], "fontSize": "24px",
                                                    "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px", "flex": "1"}),
        html.Div([
            html.Div("TOTAL GAIN/LOSS", style={"color": COLORS["text3"], "fontSize": "11px", "fontWeight": "600"}),
            html.Div(f"${total_gain:,.2f} ({total_gain_pct:+.2f}%)",
                     style={"color": gain_color, "fontSize": "24px", "fontWeight": "800",
                            "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px", "flex": "1"}),
    ], style={"display": "flex", "gap": "12px", "marginBottom": "24px"})

    # Allocation pie chart
    import plotly.graph_objects as go
    labels = [r[0] for r in rows_data]
    values = [r[4] for r in rows_data]
    pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5,
                                  marker=dict(colors=["#4b8bf5", "#4ade80", "#f59e0b", "#f87171",
                                                       "#a78bfa", "#38bdf8", "#fb923c", "#34d399"]))])
    pie.update_layout(paper_bgcolor=COLORS["panel"], font=dict(color=COLORS["text2"]),
                      margin=dict(l=0, r=0, t=10, b=10), height=300, showlegend=True)
    pie_card = html.Div([
        html.Div("ALLOCATION", style={"color": COLORS["text3"], "fontSize": "11px",
                                       "fontWeight": "600", "marginBottom": "10px"}),
        dcc.Graph(figure=pie, config={"displayModeBar": False}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "24px"})

    # Holdings table
    header = html.Div([
        html.Span("SYMBOL", style={"flex": "1", "color": COLORS["text3"], "fontSize": "11px"}),
        html.Span("SHARES", style={"flex": "1", "color": COLORS["text3"], "fontSize": "11px", "textAlign": "right"}),
        html.Span("COST", style={"flex": "1", "color": COLORS["text3"], "fontSize": "11px", "textAlign": "right"}),
        html.Span("PRICE", style={"flex": "1", "color": COLORS["text3"], "fontSize": "11px", "textAlign": "right"}),
        html.Span("VALUE", style={"flex": "1", "color": COLORS["text3"], "fontSize": "11px", "textAlign": "right"}),
        html.Span("GAIN/LOSS", style={"flex": "1.5", "color": COLORS["text3"], "fontSize": "11px", "textAlign": "right"}),
        html.Span("", style={"width": "30px"}),
    ], style={"display": "flex", "padding": "8px 16px", "gap": "8px"})

    table_rows = [header]
    for sym, shares, cost, price, value, gain, gain_pct in rows_data:
        g_color = COLORS["green"] if gain >= 0 else COLORS["red"]
        table_rows.append(html.Div([
            html.Span(sym, style={"flex": "1", "color": COLORS["text"], "fontWeight": "700",
                                  "fontFamily": FONT_MONO}),
            html.Span(f"{shares:g}", style={"flex": "1", "color": COLORS["text2"], "textAlign": "right",
                                            "fontFamily": FONT_MONO}),
            html.Span(f"${cost:.2f}", style={"flex": "1", "color": COLORS["text2"], "textAlign": "right",
                                             "fontFamily": FONT_MONO}),
            html.Span(f"${price:.2f}", style={"flex": "1", "color": COLORS["text2"], "textAlign": "right",
                                              "fontFamily": FONT_MONO}),
            html.Span(f"${value:,.2f}", style={"flex": "1", "color": COLORS["text"], "textAlign": "right",
                                               "fontFamily": FONT_MONO, "fontWeight": "600"}),
            html.Span(f"${gain:,.2f} ({gain_pct:+.1f}%)", style={"flex": "1.5", "color": g_color,
                                                                  "textAlign": "right", "fontFamily": FONT_MONO,
                                                                  "fontWeight": "700"}),
            html.Span("✕", id={"type": "pf-remove", "index": sym}, n_clicks=0,
                      style={"width": "30px", "color": COLORS["text3"], "cursor": "pointer",
                             "textAlign": "center"}),
        ], style={"display": "flex", "padding": "12px 16px", "gap": "8px", "alignItems": "center",
                  "background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "8px", "marginBottom": "6px"}))

    return html.Div([add_form, summary, pie_card, html.Div(table_rows)])
