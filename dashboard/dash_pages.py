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

    summary_box = html.Div(
        html.Div(dcc.Markdown(summary_text), style={
            "background": "#0d1a13", "border": "1px solid #1a3d2a",
            "borderLeft": f"3px solid {COLORS['green']}", "borderRadius": "8px",
            "padding": "16px 20px", "color": "#d1d5db",
        }) if summary_text else html.Div([
            html.Span("⟳ ", style={"color": COLORS["blue"]}),
            html.Span("Generating AI market analysis...",
                      style={"color": COLORS["text3"], "fontSize": "13px"}),
        ]),
        id={"type": "cat-summary-div", "cat": category},
        style={"marginBottom": "20px"}
    )

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

    # Fetch current prices - parallel
    symbols = [h["symbol"] for h in holdings]
    if _FAST_FETCH:
        prices = fetch_current_prices(symbols)
        for sym in symbols:
            if sym not in prices:
                prices[sym] = 0
    else:
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


# ---------- Sector / Geography Breakdown ----------
SECTOR_LABELS = {
    "technology": "Technology",
    "financial_services": "Financial Services",
    "healthcare": "Healthcare",
    "consumer_cyclical": "Consumer Cyclical",
    "consumer_defensive": "Consumer Defensive",
    "industrials": "Industrials",
    "communication_services": "Communication Services",
    "energy": "Energy",
    "basic_materials": "Basic Materials",
    "realestate": "Real Estate",
    "utilities": "Utilities",
}

PIE_COLORS = ["#4b8bf5", "#4ade80", "#f59e0b", "#f87171", "#a78bfa",
              "#38bdf8", "#fb923c", "#34d399", "#fbbf24", "#f472b6", "#60a5fa"]


def get_holding_sectors(sym):
    """Return dict of sector -> weight (0-1) for a holding."""
    try:
        t = yf.Ticker(sym)
        # Try ETF sector weightings first
        try:
            weights = t.funds_data.sector_weightings
            if weights:
                return {SECTOR_LABELS.get(k, k.title()): v for k, v in weights.items()}
        except Exception:
            pass
        # Fall back to single-stock sector
        sector = t.info.get("sector")
        if sector:
            return {sector: 1.0}
    except Exception:
        pass
    return {}


def get_holding_country(sym):
    """Return dict of region -> weight for a holding."""
    try:
        t = yf.Ticker(sym)
        # ETFs: try to infer from name/holdings
        info = t.info
        country = info.get("country")
        if country:
            return {country: 1.0}
        # For ETFs without country, guess US vs International from name
        name = (info.get("longName", "") or "").lower()
        if any(w in name for w in ["international", "developed", "emerging", "world", "global", "ex-us", "ex us"]):
            return {"International": 1.0}
        return {"United States": 1.0}
    except Exception:
        pass
    return {}


def breakdown_tab():
    holdings = load_portfolio()
    if not holdings:
        return html.Div("Add holdings in the Portfolio tab first to see your sector and geography exposure.",
                        style={"color": COLORS["text2"]})

    # Get current values to weight by dollar amount
    holding_values = {}
    total_value = 0
    for h in holdings:
        sym = h["symbol"]
        try:
            hist = yf.Ticker(sym).history(period="5d")
            price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else 0
        except Exception:
            price = 0
        val = h.get("shares", 0) * price
        holding_values[sym] = val
        total_value += val

    if total_value == 0:
        return html.Div("Could not fetch prices for your holdings.", style={"color": COLORS["text2"]})

    # Aggregate sectors weighted by dollar value
    sector_totals = {}
    for h in holdings:
        sym = h["symbol"]
        weight = holding_values[sym] / total_value
        for sector, sw in get_holding_sectors(sym).items():
            sector_totals[sector] = sector_totals.get(sector, 0) + sw * weight

    # Aggregate geography
    geo_totals = {}
    for h in holdings:
        sym = h["symbol"]
        weight = holding_values[sym] / total_value
        for region, rw in get_holding_country(sym).items():
            geo_totals[region] = geo_totals.get(region, 0) + rw * weight

    import plotly.graph_objects as go

    def make_pie(data_dict, title):
        items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
        labels = [k for k, v in items]
        values = [v * 100 for k, v in items]
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.5,
                                      marker=dict(colors=PIE_COLORS),
                                      textinfo="label+percent",
                                      textfont=dict(size=11))])
        fig.update_layout(paper_bgcolor=COLORS["panel"], font=dict(color=COLORS["text2"]),
                          margin=dict(l=0, r=0, t=10, b=10), height=380, showlegend=False)
        return html.Div([
            html.Div(title, style={"color": COLORS["text3"], "fontSize": "11px",
                                   "fontWeight": "600", "letterSpacing": "0.5px",
                                   "marginBottom": "10px"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px", "flex": "1"})

    # Sector detail bars
    sector_items = sorted(sector_totals.items(), key=lambda x: x[1], reverse=True)
    bars = []
    for i, (sector, weight) in enumerate(sector_items):
        pct = weight * 100
        bars.append(html.Div([
            html.Div([
                html.Span(sector, style={"color": COLORS["text"], "fontSize": "13px", "fontWeight": "600"}),
                html.Span(f"{pct:.1f}%", style={"color": COLORS["text2"], "fontSize": "13px",
                                                "fontFamily": FONT_MONO, "float": "right"}),
            ]),
            html.Div(html.Div(style={"width": f"{pct}%", "background": PIE_COLORS[i % len(PIE_COLORS)],
                                     "height": "6px", "borderRadius": "3px"}),
                     style={"background": COLORS["border"], "borderRadius": "3px", "height": "6px",
                            "marginTop": "6px"}),
        ], style={"marginBottom": "12px"}))

    return html.Div([
        html.Div([
            make_pie(sector_totals, "SECTOR EXPOSURE"),
            make_pie(geo_totals, "GEOGRAPHIC EXPOSURE"),
        ], style={"display": "flex", "gap": "12px", "marginBottom": "24px"}),
        html.Div([
            html.Div("SECTOR DETAIL", style={"color": COLORS["text3"], "fontSize": "11px",
                                             "fontWeight": "600", "letterSpacing": "0.5px",
                                             "marginBottom": "16px"}),
            html.Div(bars),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "20px"}),
    ])


# ---------- Correlation Matrix ----------
def correlation_tab():
    holdings = load_portfolio()
    symbols = [h["symbol"] for h in holdings]

    if len(symbols) < 2:
        return html.Div("Add at least 2 holdings in the Portfolio tab to see how they correlate.",
                        style={"color": COLORS["text2"]})

    # Fetch 1 year of daily returns
    import numpy as np
    price_data = {}
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(period="1y")
            if not hist.empty:
                price_data[sym] = hist["Close"]
        except Exception:
            continue

    valid_symbols = list(price_data.keys())
    if len(valid_symbols) < 2:
        return html.Div("Could not fetch enough price history for correlation.",
                        style={"color": COLORS["text2"]})

    # Build returns dataframe
    import pandas as pd
    df = pd.DataFrame(price_data)
    returns = df.pct_change().dropna()
    corr = returns.corr()

    import plotly.graph_objects as go
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale=[[0, "#0d1219"], [0.5, "#1e3a5f"], [1, "#4b8bf5"]],
        zmin=-1, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in corr.values],
        texttemplate="%{text}",
        textfont=dict(size=13, color="#e2e8f0"),
        showscale=True,
        colorbar=dict(tickfont=dict(color="#94a3b8")),
    ))
    fig.update_layout(
        paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
        font=dict(color=COLORS["text2"]),
        margin=dict(l=0, r=0, t=10, b=0), height=450,
        xaxis=dict(side="bottom"), yaxis=dict(autorange="reversed"),
    )

    # Find highest correlated pairs (diversification warning)
    warnings = []
    for i in range(len(valid_symbols)):
        for j in range(i + 1, len(valid_symbols)):
            c = corr.iloc[i, j]
            if c > 0.85:
                warnings.append((valid_symbols[i], valid_symbols[j], c))
    warnings.sort(key=lambda x: x[2], reverse=True)

    warning_cards = []
    if warnings:
        warning_cards.append(html.Div("⚠️ HIGHLY CORRELATED PAIRS (low diversification)",
                                       style={"color": COLORS["amber"], "fontSize": "11px",
                                              "fontWeight": "600", "letterSpacing": "0.5px",
                                              "margin": "20px 0 12px"}))
        for a, b, c in warnings:
            warning_cards.append(html.Div([
                html.Span(f"{a} ↔ {b}", style={"color": COLORS["text"], "fontWeight": "600",
                                               "fontFamily": FONT_MONO}),
                html.Span(f"{c:.2f} correlation", style={"color": COLORS["amber"],
                                                         "float": "right", "fontFamily": FONT_MONO}),
            ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                      "borderLeft": f"3px solid {COLORS['amber']}", "borderRadius": "8px",
                      "padding": "10px 16px", "marginBottom": "6px"}))

    return html.Div([
        html.Div("How your holdings move together over the past year. 1.00 = move identically (no diversification benefit), 0 = independent, negative = move opposite (best diversification).",
                 style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"}),
        html.Div([
            html.Div("CORRELATION MATRIX", style={"color": COLORS["text3"], "fontSize": "11px",
                                                  "fontWeight": "600", "letterSpacing": "0.5px",
                                                  "marginBottom": "12px"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "20px", "marginBottom": "12px"}),
        html.Div(warning_cards),
    ])


# ---------- Treemaps / Market Maps ----------
MAP_STOCKS = {
    "Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "ADBE", "TXN", "QCOM"],
    "Communication": ["GOOGL", "META", "NFLX", "DIS", "T", "VZ", "TMUS", "CMCSA"],
    "Consumer": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "COST", "WMT", "PG", "KO"],
    "Financials": ["JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP"],
    "Healthcare": ["UNH", "JNJ", "LLY", "PFE", "MRK", "ABBV", "TMO", "ABT", "DHR", "AMGN"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG"],
    "Industrials": ["CAT", "GE", "RTX", "HON", "UPS", "BA", "DE"],
}


def _treemap_data(symbols_flat):
    """Fetch price changes for a list of symbols."""
    results = {}
    try:
        data = yf.download(symbols_flat, period="2d", progress=False, group_by="ticker")
        for sym in symbols_flat:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    pct = ((curr - prev) / prev) * 100
                    results[sym] = pct
            except Exception:
                continue
    except Exception:
        pass
    return results


def _make_treemap(labels, parents, values, colors, title=""):
    import plotly.graph_objects as go
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            colorscale=[[0, "#7f1d1d"], [0.25, "#dc2626"], [0.5, "#1f2937"], [0.75, "#16a34a"], [1, "#14532d"]],
            cmid=0, cmin=-3, cmax=3,
            line=dict(width=2, color="#080c12"),
        ),
        textinfo="label+text",
        textfont=dict(size=13, color="#ffffff"),
        tiling=dict(pad=2),
    ))
    fig.update_layout(
        paper_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=0, b=0), height=600,
        font=dict(family=FONT_MONO),
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def market_treemap():
    all_syms = [s for syms in MAP_STOCKS.values() for s in syms]
    changes = _treemap_data(all_syms)
    # Parallel market cap fetch with cache
    from cache_utils import cache_get, cache_set
    caps = cache_get("market_caps", ttl=1800)
    if not caps:
        if _FAST_FETCH:
            all_info = fetch_many_info(all_syms, max_workers=15)
            caps = {sym: (all_info.get(sym, {}).get("marketCap", 0) or 0) for sym in all_syms}
        else:
            caps = {}
            for sym in all_syms:
                try:
                    caps[sym] = yf.Ticker(sym).info.get("marketCap", 0) or 0
                except Exception:
                    caps[sym] = 0
        cache_set("market_caps", caps, ttl=1800)

    labels, parents, values, colors, texts = ["Market"], [""], [0], [0], [""]
    for sector, syms in MAP_STOCKS.items():
        labels.append(sector)
        parents.append("Market")
        values.append(0)
        colors.append(0)
        texts.append("")
        for sym in syms:
            if sym in changes and caps.get(sym, 0) > 0:
                labels.append(sym)
                parents.append(sector)
                values.append(caps[sym] / 1e9)
                colors.append(changes[sym])
                texts.append(f"{changes[sym]:+.2f}%")

    import plotly.graph_objects as go
    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors,
                    colorscale=[[0, "#7f1d1d"], [0.25, "#dc2626"], [0.5, "#1f2937"], [0.75, "#16a34a"], [1, "#14532d"]],
                    cmid=0, cmin=-3, cmax=3, line=dict(width=2, color="#080c12")),
        text=texts, textinfo="label+text", textposition="middle center",
        textfont=dict(size=14, color="#ffffff", family=FONT_MONO),
        tiling=dict(pad=1),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(paper_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=0, b=0),
                      height=680, font=dict(family=FONT_MONO))
    return dcc.Graph(figure=fig, id="market-treemap-graph", config={"displayModeBar": False})


def portfolio_treemap():
    holdings = load_portfolio()
    if not holdings:
        return html.Div("Add holdings in the Portfolio tab first.", style={"color": COLORS["text2"]})
    syms = [h["symbol"] for h in holdings]
    changes = _treemap_data(syms)
    labels, parents, values, colors, texts = ["Portfolio"], [""], [0], [0], [""]
    for h in holdings:
        sym = h["symbol"]
        try:
            hist = yf.Ticker(sym).history(period="5d")
            price = float(hist["Close"].dropna().iloc[-1]) if not hist.empty else 0
        except Exception:
            price = 0
        value = h.get("shares", 0) * price
        if value > 0:
            labels.append(sym)
            parents.append("Portfolio")
            values.append(value)
            colors.append(changes.get(sym, 0))
            texts.append(f"${value:,.0f}\n{changes.get(sym, 0):+.2f}%")

    import plotly.graph_objects as go
    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors,
                    colorscale=[[0, "#7f1d1d"], [0.25, "#dc2626"], [0.5, "#1f2937"], [0.75, "#16a34a"], [1, "#14532d"]],
                    cmid=0, cmin=-3, cmax=3, line=dict(width=2, color="#080c12")),
        text=texts, textinfo="label+text",
        textfont=dict(size=14, color="#ffffff"), tiling=dict(pad=2),
    ))
    fig.update_layout(paper_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=0, b=0),
                      height=600, font=dict(family=FONT_MONO))
    return dcc.Graph(figure=fig, id="portfolio-treemap-graph", config={"displayModeBar": False})


def sector_treemap():
    all_syms = [s for syms in MAP_STOCKS.values() for s in syms]
    changes = _treemap_data(all_syms)
    from cache_utils import cache_get
    caps = cache_get("market_caps", ttl=1800) or {}
    if not caps:
        if _FAST_FETCH:
            all_info = fetch_many_info(all_syms, max_workers=15)
            caps = {sym: (all_info.get(sym, {}).get("marketCap", 0) or 0) for sym in all_syms}
        else:
            for sym in all_syms:
                try:
                    caps[sym] = yf.Ticker(sym).info.get("marketCap", 0) or 0
                except Exception:
                    caps[sym] = 0

    # Aggregate by sector - avg change weighted by cap
    labels, parents, values, colors, texts = ["Sectors"], [""], [0], [0], [""]
    for sector, syms in MAP_STOCKS.items():
        total_cap = sum(caps.get(s, 0) for s in syms)
        if total_cap == 0:
            continue
        weighted_change = sum(changes.get(s, 0) * caps.get(s, 0) for s in syms) / total_cap
        labels.append(sector)
        parents.append("Sectors")
        values.append(total_cap / 1e9)
        colors.append(weighted_change)
        texts.append(f"{weighted_change:+.2f}%")

    import plotly.graph_objects as go
    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors,
                    colorscale=[[0, "#7f1d1d"], [0.25, "#dc2626"], [0.5, "#1f2937"], [0.75, "#16a34a"], [1, "#14532d"]],
                    cmid=0, cmin=-2, cmax=2, line=dict(width=2, color="#080c12")),
        text=texts, textinfo="label+text",
        textfont=dict(size=16, color="#ffffff"), tiling=dict(pad=3),
    ))
    fig.update_layout(paper_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=0, b=0),
                      height=600, font=dict(family=FONT_MONO))
    return dcc.Graph(figure=fig, config={"displayModeBar": False})


def _color_legend():
    stops = [("-3%", "#7f1d1d"), ("-1.5%", "#dc2626"), ("0%", "#1f2937"),
             ("+1.5%", "#16a34a"), ("+3%", "#14532d")]
    cells = []
    for label, color in stops:
        cells.append(html.Div([
            html.Div(style={"width": "40px", "height": "14px", "background": color,
                            "borderRadius": "2px"}),
            html.Div(label, style={"color": COLORS["text3"], "fontSize": "10px",
                                   "marginTop": "3px", "textAlign": "center",
                                   "fontFamily": FONT_MONO}),
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"}))
    return html.Div(cells, style={"display": "flex", "gap": "8px", "justifyContent": "flex-end",
                                  "marginBottom": "8px"})


def market_map_tab():
    return html.Div([
        dbc.Tabs([
            dbc.Tab(label="🌎 Market", tab_id="map-market"),
            dbc.Tab(label="📊 ETFs", tab_id="map-etfs"),
            dbc.Tab(label="💼 Portfolio", tab_id="map-portfolio"),
            dbc.Tab(label="🏢 Sectors", tab_id="map-sectors"),
        ], id="map-subtabs", active_tab="map-market"),
        _color_legend(),
        dcc.Loading(html.Div(id="map-subtab-content", style={"marginTop": "8px"}),
                    type="circle", color="#4b8bf5"),
    ])


# ---------- ETF Treemap ----------
MAP_ETFS = {
    "Broad Market": ["SPY", "QQQ", "VTI", "VOO", "IWM", "DIA"],
    "Sectors": ["XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"],
    "Tech/Growth": ["VGT", "ARKK", "SMH", "SOXX", "FTEC"],
    "Bonds": ["BND", "AGG", "TLT", "LQD", "HYG"],
    "Commodities/Intl": ["GLD", "SLV", "SCHF", "VXUS", "EEM", "VNQ"],
}


def etf_treemap():
    all_syms = [s for syms in MAP_ETFS.values() for s in syms]
    changes = _treemap_data(all_syms)
    cache_key = "etf_caps"
    from cache_utils import cache_get, cache_set
    caps = cache_get(cache_key, ttl=1800) or {}
    if not caps:
        if _FAST_FETCH:
            all_info = fetch_many_info(all_syms, max_workers=10)
            caps = {sym: (all_info.get(sym, {}).get("totalAssets") or
                          all_info.get(sym, {}).get("marketCap") or 1e9)
                    for sym in all_syms}
        else:
            for sym in all_syms:
                try:
                    caps[sym] = yf.Ticker(sym).info.get("totalAssets", 0) or 1e9
                except Exception:
                    caps[sym] = 1e9
        cache_set(cache_key, caps, ttl=1800)

    labels, parents, values, colors, texts = ["ETFs"], [""], [0], [0], [""]
    for group, syms in MAP_ETFS.items():
        labels.append(group)
        parents.append("ETFs")
        values.append(0)
        colors.append(0)
        texts.append("")
        for sym in syms:
            if sym in changes:
                labels.append(sym)
                parents.append(group)
                values.append(caps.get(sym, 1e9) / 1e9)
                colors.append(changes[sym])
                texts.append(f"{changes[sym]:+.2f}%")

    import plotly.graph_objects as go
    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors,
                    colorscale=[[0, "#7f1d1d"], [0.25, "#dc2626"], [0.5, "#1f2937"],
                                [0.75, "#16a34a"], [1, "#14532d"]],
                    cmid=0, cmin=-3, cmax=3, line=dict(width=2, color="#080c12")),
        text=texts, textinfo="label+text", textposition="middle center",
        textfont=dict(size=14, color="#ffffff", family=FONT_MONO), tiling=dict(pad=1),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(paper_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=0, b=0),
                      height=680, font=dict(family=FONT_MONO))
    return dcc.Graph(figure=fig, id="etf-treemap-graph", config={"displayModeBar": False})


# ---------- Performance imports ----------
try:
    from fetch_utils import fetch_many_info, fetch_many_history, fetch_current_prices
    from cache_utils import mem_get, mem_set, cache_get, cache_set, cache_clean
    _FAST_FETCH = True
except ImportError:
    _FAST_FETCH = False

# ---------- Compare Mode ----------
def compare_input_row():
    return html.Div([
        html.Div("COMPARE TICKERS (up to 4)", style={"color": COLORS["text3"], "fontSize": "11px",
                                                     "fontWeight": "600", "letterSpacing": "0.5px",
                                                     "marginBottom": "10px"}),
        html.Div([
            dbc.Input(id="compare-input", placeholder="Add ticker (e.g. VTI)",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Button("Add", id="compare-add-btn", color="primary", size="sm"),
            dbc.Button("Clear All", id="compare-clear-btn", color="secondary", size="sm",
                       outline=True, className="ms-2"),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),
    ])


def compare_results(symbols=None):
    symbols = symbols or []
    if not symbols:
        return html.Div("Add 2-4 tickers above to compare them side by side.",
                        style={"color": COLORS["text2"]})

    # Chips showing selected tickers
    chips = html.Div([
        html.Span([
            sym,
            html.Span(" ✕", id={"type": "compare-remove", "index": sym},
                      n_clicks=0, style={"cursor": "pointer", "marginLeft": "6px",
                                         "color": COLORS["text3"]}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                  "borderRadius": "6px", "padding": "6px 12px", "marginRight": "8px",
                  "color": COLORS["text"], "fontFamily": FONT_MONO, "fontSize": "13px"})
        for sym in symbols
    ], style={"marginBottom": "20px"})

    # Overlaid normalized price chart (all start at 100 for fair comparison)
    import plotly.graph_objects as go
    chart_colors = ["#4b8bf5", "#4ade80", "#f59e0b", "#f87171"]
    fig = go.Figure()
    for i, sym in enumerate(symbols):
        try:
            hist = yf.Ticker(sym).history(period="1y")
            if not hist.empty:
                closes = hist["Close"]
                normalized = (closes / closes.iloc[0]) * 100
                fig.add_trace(go.Scatter(x=hist.index, y=normalized, mode="lines",
                                         name=sym, line=dict(color=chart_colors[i % 4], width=2)))
        except Exception:
            continue
    fig.update_layout(
        paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
        font=dict(color=COLORS["text2"]),
        xaxis=dict(gridcolor=COLORS["border"]), yaxis=dict(gridcolor=COLORS["border"], title="Normalized (start=100)"),
        margin=dict(l=0, r=0, t=10, b=0), height=380, legend=dict(orientation="h"),
    )
    chart_card = html.Div([
        html.Div("1-YEAR PERFORMANCE (normalized to 100)", style={"color": COLORS["text3"],
                 "fontSize": "11px", "fontWeight": "600", "marginBottom": "10px"}),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "20px"})

    # Comparison table of ratios
    metrics = [
        ("Price", lambda i: f"${i.get('currentPrice') or i.get('regularMarketPrice', 0) or 0:,.2f}"),
        ("Market Cap", lambda i: f"${(i.get('marketCap', 0) or 0)/1e9:.1f}B" if i.get('marketCap') else "N/A"),
        ("P/E Ratio", lambda i: f"{i.get('trailingPE'):.2f}" if i.get('trailingPE') else "N/A"),
        ("Forward P/E", lambda i: f"{i.get('forwardPE'):.2f}" if i.get('forwardPE') else "N/A"),
        ("P/B Ratio", lambda i: f"{i.get('priceToBook'):.2f}" if i.get('priceToBook') else "N/A"),
        ("Profit Margin", lambda i: f"{i.get('profitMargins')*100:.1f}%" if i.get('profitMargins') else "N/A"),
        ("Rev Growth", lambda i: f"{i.get('revenueGrowth')*100:.1f}%" if i.get('revenueGrowth') else "N/A"),
        ("Div Yield", lambda i: f"{i.get('dividendYield')*100:.2f}%" if i.get('dividendYield') else "N/A"),
        ("52W High", lambda i: f"${i.get('fiftyTwoWeekHigh', 0) or 0:,.2f}" if i.get('fiftyTwoWeekHigh') else "N/A"),
        ("52W Low", lambda i: f"${i.get('fiftyTwoWeekLow', 0) or 0:,.2f}" if i.get('fiftyTwoWeekLow') else "N/A"),
        ("Beta", lambda i: f"{i.get('beta'):.2f}" if i.get('beta') else "N/A"),
    ]

    infos = {}
    for sym in symbols:
        try:
            infos[sym] = yf.Ticker(sym).info
        except Exception:
            infos[sym] = {}

    # Header row
    header = html.Div([html.Span("METRIC", style={"flex": "1.5", "color": COLORS["text3"],
                                                   "fontSize": "11px", "fontWeight": "600"})] +
                      [html.Span(sym, style={"flex": "1", "color": COLORS["text"], "fontSize": "13px",
                                             "fontWeight": "700", "textAlign": "right",
                                             "fontFamily": FONT_MONO}) for sym in symbols],
                      style={"display": "flex", "padding": "10px 16px", "gap": "12px",
                             "borderBottom": f"1px solid {COLORS['border']}"})

    metric_rows = [header]
    for label, fn in metrics:
        cells = [html.Span(label, style={"flex": "1.5", "color": COLORS["text2"], "fontSize": "13px"})]
        for sym in symbols:
            cells.append(html.Span(fn(infos[sym]), style={"flex": "1", "color": COLORS["text"],
                                                           "fontSize": "13px", "textAlign": "right",
                                                           "fontFamily": FONT_MONO}))
        metric_rows.append(html.Div(cells, style={"display": "flex", "padding": "10px 16px",
                                                   "gap": "12px",
                                                   "borderBottom": f"1px solid {COLORS['border']}"}))

    table_card = html.Div(metric_rows, style={"background": COLORS["panel"],
                          "border": f"1px solid {COLORS['border']}", "borderRadius": "10px"})

    return html.Div([chips, chart_card, table_card])


def compare_tab(symbols=None):
    return html.Div([
        compare_input_row(),
        html.Div(compare_results(symbols), id="compare-results"),
    ])


# ---------- Economic Indicators ----------
import requests as _req

FRED_SERIES = {
    "Fed Funds Rate": ("FEDFUNDS", "%", "#4b8bf5"),
    "CPI Inflation (YoY)": ("CPIAUCSL", "%", "#f59e0b"),
    "Unemployment Rate": ("UNRATE", "%", "#f87171"),
    "10Y Treasury Yield": ("DGS10", "%", "#4ade80"),
    "2Y Treasury Yield": ("DGS2", "%", "#a78bfa"),
    "GDP Growth (QoQ)": ("A191RL1Q225SBEA", "%", "#38bdf8"),
}


def _fetch_fred(series_id, limit=60):
    key = os.getenv("FRED_API_KEY")
    try:
        resp = _req.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": key, "file_type": "json",
                    "sort_order": "desc", "limit": limit},
            timeout=15,
        )
        data = resp.json()
        obs = data.get("observations", [])
        dates, values = [], []
        for o in reversed(obs):
            v = o.get("value", ".")
            if v != ".":
                dates.append(o["date"])
                values.append(float(v))
        return dates, values
    except Exception:
        return [], []


def economic_tab():
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # Fetch all FRED series in parallel
    from concurrent.futures import ThreadPoolExecutor, as_completed
    series_data = {}
    def _fetch_one(item):
        label, (series_id, unit, color) = item
        dates, values = _fetch_fred(series_id)
        return label, (dates, values, unit, color)
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_fetch_one, item): item for item in FRED_SERIES.items()}
        for future in as_completed(futures):
            label, data = future.result()
            series_data[label] = data

    # Current values summary cards
    cards = []
    for label, (dates, values, unit, color) in series_data.items():
        if not values:
            continue
        current = values[-1]
        prev = values[-2] if len(values) > 1 else current
        change = current - prev
        arrow = "▲" if change >= 0 else "▼"
        change_color = COLORS["green"] if change >= 0 else COLORS["red"]
        # Special case: unemployment up = bad
        if "Unemployment" in label:
            change_color = COLORS["red"] if change >= 0 else COLORS["green"]
        cards.append(html.Div([
            html.Div(label, style={"color": COLORS["text3"], "fontSize": "10px",
                                   "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(f"{current:.2f}{unit}", style={"color": color, "fontSize": "22px",
                                                     "fontWeight": "800", "fontFamily": FONT_MONO,
                                                     "margin": "4px 0 2px"}),
            html.Div(f"{arrow} {abs(change):.2f}{unit} vs prior",
                     style={"color": change_color, "fontSize": "11px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderLeft": f"3px solid {color}", "borderRadius": "10px",
                  "padding": "14px 18px", "flex": "1"}))

    summary_row = html.Div(cards, style={"display": "flex", "gap": "10px", "marginBottom": "24px",
                                          "flexWrap": "wrap"})

    # Yield curve (2Y vs 10Y spread)
    y2_dates, y2_vals = series_data.get("2Y Treasury Yield", ([], [], None, None))[:2]
    y10_dates, y10_vals = series_data.get("10Y Treasury Yield", ([], [], None, None))[:2]

    yield_curve_card = html.Div()
    if y2_vals and y10_vals:
        min_len = min(len(y2_vals), len(y10_vals))
        spread = [y10_vals[i] - y2_vals[i] for i in range(min_len)]
        spread_dates = y10_dates[-min_len:]
        spread_color = COLORS["green"] if spread[-1] > 0 else COLORS["red"]
        status = "Normal" if spread[-1] > 0 else "⚠️ INVERTED (recession signal)"
        fig_yc = go.Figure()
        fig_yc.add_trace(go.Scatter(x=spread_dates, y=spread, mode="lines",
                                     line=dict(color=spread_color, width=2), fill="tozeroy",
                                     fillcolor=f"rgba({','.join(str(int(spread_color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.15)"))
        fig_yc.add_hline(y=0, line_dash="dash", line_color=COLORS["text3"])
        fig_yc.update_layout(paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
                              font=dict(color=COLORS["text2"]),
                              xaxis=dict(gridcolor=COLORS["border"]),
                              yaxis=dict(gridcolor=COLORS["border"], title="Spread (%)"),
                              margin=dict(l=0, r=0, t=10, b=0), height=200)
        yield_curve_card = html.Div([
            html.Div([
                html.Span("YIELD CURVE (10Y - 2Y SPREAD)", style={"color": COLORS["text3"],
                          "fontSize": "11px", "fontWeight": "600"}),
                html.Span(f"  {spread[-1]:+.2f}%  {status}",
                          style={"color": spread_color, "fontSize": "12px", "fontWeight": "700",
                                 "marginLeft": "12px"}),
            ], style={"marginBottom": "10px"}),
            dcc.Graph(figure=fig_yc, config={"displayModeBar": False}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "20px"})

    # Individual indicator charts in a 2-column grid
    chart_cards = []
    for label, (dates, values, unit, color) in series_data.items():
        if not dates:
            continue
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=values, mode="lines",
                                  line=dict(color=color, width=2), fill="tozeroy",
                                  fillcolor=f"rgba({','.join(str(int(color.lstrip('#')[i:i+2], 16)) for i in (0,2,4))},0.1)"))
        fig.update_layout(paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
                          font=dict(color=COLORS["text2"]),
                          xaxis=dict(gridcolor=COLORS["border"], showgrid=True),
                          yaxis=dict(gridcolor=COLORS["border"], showgrid=True),
                          margin=dict(l=0, r=0, t=10, b=0), height=200)
        chart_cards.append(html.Div([
            html.Div(label, style={"color": COLORS["text3"], "fontSize": "11px",
                                   "fontWeight": "600", "marginBottom": "8px"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px"}))

    charts_grid = html.Div(chart_cards, style={"display": "grid",
                           "gridTemplateColumns": "repeat(2, 1fr)", "gap": "12px"})

    return html.Div([
        html.Div("Key economic indicators from the Federal Reserve (FRED). Updated monthly.",
                 style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"}),
        summary_row,
        yield_curve_card,
        charts_grid,
    ])


# ---------- Backtesting ----------
import numpy as np
import pandas as pd


def run_backtest(weights_dict, start_date="2015-01-01", initial_value=10000):
    """
    weights_dict: {"VTI": 0.6, "SCHF": 0.3, "BND": 0.1}
    Returns a dict of results.
    """
    symbols = list(weights_dict.keys())
    weights = np.array([weights_dict[s] for s in symbols])

    # Download historical data
    price_data = {}
    for sym in symbols:
        try:
            hist = yf.Ticker(sym).history(start=start_date)
            if not hist.empty:
                price_data[sym] = hist["Close"]
        except Exception:
            continue

    if len(price_data) < 1:
        return None

    df = pd.DataFrame(price_data).dropna()
    if df.empty:
        return None

    # Normalize weights to what we have data for
    valid_syms = [s for s in symbols if s in df.columns]
    valid_weights = np.array([weights_dict[s] for s in valid_syms])
    valid_weights = valid_weights / valid_weights.sum()

    # Daily returns
    returns = df[valid_syms].pct_change().dropna()

    # Portfolio returns (rebalanced daily for simplicity)
    port_returns = (returns * valid_weights).sum(axis=1)

    # Cumulative portfolio value
    port_value = (1 + port_returns).cumprod() * initial_value

    # Benchmark: SPY
    try:
        spy_hist = yf.Ticker("SPY").history(start=start_date)
        spy_close = spy_hist["Close"].reindex(df.index, method="ffill").dropna()
        spy_returns = spy_close.pct_change().dropna()
        spy_value = (1 + spy_returns).cumprod() * initial_value
    except Exception:
        spy_value = None
        spy_returns = None

    # Metrics
    total_return = (port_value.iloc[-1] / initial_value - 1) * 100
    years = len(port_returns) / 252
    cagr = ((port_value.iloc[-1] / initial_value) ** (1 / years) - 1) * 100 if years > 0 else 0

    # Sharpe ratio (assumes risk-free rate of 4%)
    rf_daily = 0.04 / 252
    excess = port_returns - rf_daily
    sharpe = (excess.mean() / excess.std()) * np.sqrt(252) if excess.std() > 0 else 0

    # Max drawdown
    rolling_max = port_value.cummax()
    drawdown = (port_value - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100

    # Annual returns
    annual = port_returns.resample("YE").apply(lambda x: (1 + x).prod() - 1) * 100

    return {
        "port_value": port_value,
        "spy_value": spy_value,
        "port_returns": port_returns,
        "spy_returns": spy_returns,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "annual_returns": annual,
        "years": years,
        "final_value": port_value.iloc[-1],
    }


def backtest_tab(weights_dict=None, start_date="2015-01-01"):
    weights_dict = weights_dict or {}

    # Allocation input form
    portfolio_holdings = load_portfolio()
    portfolio_syms = [h["symbol"] for h in portfolio_holdings]

    form = html.Div([
        html.Div("BACKTEST ALLOCATION", style={"color": COLORS["text3"], "fontSize": "11px",
                                               "fontWeight": "600", "letterSpacing": "0.5px",
                                               "marginBottom": "10px"}),
        html.Div("Enter allocation weights (must sum to 100%)",
                 style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "12px"}),
        html.Div([
            dbc.Input(id="bt-allocation", placeholder='e.g. VTI:60,SCHF:30,BND:10',
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Select(id="bt-start", options=[
                {"label": "5 Years", "value": "2020-01-01"},
                {"label": "10 Years", "value": "2015-01-01"},
                {"label": "15 Years", "value": "2010-01-01"},
                {"label": "20 Years", "value": "2005-01-01"},
            ], value="2015-01-01",
            style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                   "color": COLORS["text"], "marginRight": "8px", "width": "140px"}),
            dbc.Button("Run Backtest", id="bt-run-btn", color="primary", size="sm"),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"}),
    ])

    # Prefill suggestion from portfolio
    prefill = ""
    if portfolio_syms:
        n = len(portfolio_syms)
        equal_weight = round(100 / n)
        prefill = ",".join(f"{s}:{equal_weight}" for s in portfolio_syms)
        form.children.append(
            html.Div(f"💡 Your portfolio: {prefill}",
                     style={"color": COLORS["text3"], "fontSize": "11px", "marginBottom": "16px"})
        )

    if not weights_dict:
        return html.Div([form,
                         html.Div(id="bt-results",
                                  children=html.Div("Enter an allocation above and click Run Backtest.",
                                                    style={"color": COLORS["text2"]}))])

    # Run the backtest
    result = run_backtest(weights_dict, start_date)
    if not result:
        return html.Div([form,
                         html.Div(id="bt-results",
                                  children=html.Div("Could not fetch data for the selected tickers.",
                                                    style={"color": COLORS["text2"]}))])

    # Metric cards
    metrics = [
        ("TOTAL RETURN", f"{result['total_return']:+.1f}%",
         COLORS["green"] if result["total_return"] > 0 else COLORS["red"]),
        ("CAGR", f"{result['cagr']:+.2f}%/yr",
         COLORS["green"] if result["cagr"] > 0 else COLORS["red"]),
        ("SHARPE RATIO", f"{result['sharpe']:.2f}",
         COLORS["green"] if result["sharpe"] > 1 else COLORS["amber"] if result["sharpe"] > 0 else COLORS["red"]),
        ("MAX DRAWDOWN", f"{result['max_drawdown']:.1f}%", COLORS["red"]),
        ("FINAL VALUE", f"${result['final_value']:,.0f}", COLORS["text"]),
        ("YEARS", f"{result['years']:.1f}", COLORS["text2"]),
    ]

    metric_cards = html.Div([
        html.Div([
            html.Div(label, style={"color": COLORS["text3"], "fontSize": "10px",
                                   "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(value, style={"color": color, "fontSize": "20px", "fontWeight": "800",
                                   "fontFamily": FONT_MONO, "marginTop": "4px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"})
        for label, value, color in metrics
    ], style={"display": "flex", "gap": "10px", "marginBottom": "20px", "flexWrap": "wrap"})

    # Performance chart vs SPY
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=result["port_value"].index, y=result["port_value"],
                             mode="lines", name="Portfolio",
                             line=dict(color=COLORS["blue"], width=2)))
    if result["spy_value"] is not None:
        fig.add_trace(go.Scatter(x=result["spy_value"].index, y=result["spy_value"],
                                 mode="lines", name="SPY (Benchmark)",
                                 line=dict(color=COLORS["text3"], width=1.5, dash="dot")))
    fig.update_layout(paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
                      font=dict(color=COLORS["text2"]),
                      xaxis=dict(gridcolor=COLORS["border"]),
                      yaxis=dict(gridcolor=COLORS["border"], title="Portfolio Value ($)"),
                      legend=dict(orientation="h"),
                      margin=dict(l=0, r=0, t=10, b=0), height=350)
    perf_chart = html.Div([
        html.Div("PORTFOLIO GROWTH vs SPY", style={"color": COLORS["text3"], "fontSize": "11px",
                                                    "fontWeight": "600", "marginBottom": "10px"}),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "16px"})

    # Drawdown chart
    rolling_max = result["port_value"].cummax()
    drawdown_series = (result["port_value"] - rolling_max) / rolling_max * 100
    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(x=drawdown_series.index, y=drawdown_series,
                                mode="lines", fill="tozeroy",
                                line=dict(color=COLORS["red"], width=1.5),
                                fillcolor="rgba(248,113,113,0.15)"))
    fig_dd.update_layout(paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
                         font=dict(color=COLORS["text2"]),
                         xaxis=dict(gridcolor=COLORS["border"]),
                         yaxis=dict(gridcolor=COLORS["border"], title="Drawdown (%)"),
                         margin=dict(l=0, r=0, t=10, b=0), height=200)
    dd_chart = html.Div([
        html.Div("DRAWDOWN", style={"color": COLORS["text3"], "fontSize": "11px",
                                    "fontWeight": "600", "marginBottom": "10px"}),
        dcc.Graph(figure=fig_dd, config={"displayModeBar": False}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "16px"})

    # Annual returns bar chart
    annual = result["annual_returns"]
    bar_colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in annual.values]
    fig_ann = go.Figure()
    fig_ann.add_trace(go.Bar(x=[str(d.year) for d in annual.index], y=annual.values,
                              marker_color=bar_colors, text=[f"{v:.1f}%" for v in annual.values],
                              textposition="outside", textfont=dict(color=COLORS["text2"], size=11)))
    fig_ann.update_layout(paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
                          font=dict(color=COLORS["text2"]),
                          xaxis=dict(gridcolor=COLORS["border"]),
                          yaxis=dict(gridcolor=COLORS["border"], title="Return (%)"),
                          margin=dict(l=0, r=0, t=10, b=0), height=250)
    ann_chart = html.Div([
        html.Div("ANNUAL RETURNS", style={"color": COLORS["text3"], "fontSize": "11px",
                                          "fontWeight": "600", "marginBottom": "10px"}),
        dcc.Graph(figure=fig_ann, config={"displayModeBar": False}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "16px 20px"})

    results_div = html.Div([metric_cards, perf_chart, dd_chart, ann_chart])
    return html.Div([form, html.Div(id="bt-results", children=results_div)])


# ---------- Alerts ----------
ALERTS_FILE = os.path.expanduser("~/tradingbot/config/alerts.json")


def load_alerts():
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def save_alerts(alerts):
    try:
        with open(ALERTS_FILE, "w") as f:
            json.dump(alerts, f)
    except Exception:
        pass


def check_alerts():
    """Check all alerts against current prices. Returns list of triggered alerts."""
    alerts = load_alerts()
    triggered = []
    for a in alerts:
        if a.get("triggered"):
            continue
        sym = a["symbol"]
        condition = a["condition"]  # "above" or "below"
        target = a["target"]
        try:
            hist = yf.Ticker(sym).history(period="1d")
            if hist.empty:
                continue
            price = float(hist["Close"].iloc[-1])
            if condition == "above" and price >= target:
                a["triggered"] = True
                a["trigger_price"] = price
                triggered.append(a)
            elif condition == "below" and price <= target:
                a["triggered"] = True
                a["trigger_price"] = price
                triggered.append(a)
        except Exception:
            continue
    save_alerts(alerts)
    return triggered


def alerts_tab():
    alerts = load_alerts()

    form = html.Div([
        html.Div("ADD ALERT", style={"color": COLORS["text3"], "fontSize": "11px",
                                     "fontWeight": "600", "letterSpacing": "0.5px",
                                     "marginBottom": "10px"}),
        html.Div([
            dbc.Input(id="alert-symbol", placeholder="Ticker (e.g. AAPL)",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Select(id="alert-condition",
                       options=[{"label": "rises above", "value": "above"},
                                {"label": "drops below", "value": "below"}],
                       value="above",
                       style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                              "color": COLORS["text"], "marginRight": "8px", "width": "160px"}),
            dbc.Input(id="alert-target", placeholder="Price ($)", type="number",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "marginRight": "8px", "width": "130px"}),
            dbc.Button("Add Alert", id="alert-add-btn", color="primary", size="sm"),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),
    ])

    if not alerts:
        return html.Div([form,
                         html.Div(id="alerts-list",
                                  children=html.Div("No alerts set. Add one above.",
                                                    style={"color": COLORS["text2"]}))])

    rows = []
    for i, a in enumerate(alerts):
        triggered = a.get("triggered", False)
        sym = a["symbol"]
        condition = a["condition"]
        target = a["target"]
        trigger_price = a.get("trigger_price")

        status_color = COLORS["green"] if triggered else COLORS["text3"]
        status_text = f"✅ TRIGGERED @ ${trigger_price:.2f}" if triggered else "⏳ Watching"
        border_color = COLORS["green"] if triggered else COLORS["border"]

        rows.append(html.Div([
            html.Div([
                html.Span(sym, style={"color": COLORS["text"], "fontWeight": "700",
                                      "fontSize": "14px", "fontFamily": FONT_MONO,
                                      "marginRight": "12px"}),
                html.Span(f"{condition} ${target:,.2f}",
                          style={"color": COLORS["text2"], "fontSize": "13px"}),
            ], style={"flex": "1"}),
            html.Span(status_text, style={"color": status_color, "fontSize": "12px",
                                          "fontWeight": "600", "marginRight": "16px"}),
            html.Div("✕", id={"type": "alert-remove", "index": i}, n_clicks=0,
                     style={"color": COLORS["text3"], "cursor": "pointer",
                            "fontSize": "14px", "fontWeight": "700", "padding": "2px 8px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {border_color}",
                  "borderLeft": f"3px solid {border_color}",
                  "borderRadius": "8px", "padding": "12px 16px", "marginBottom": "8px",
                  "display": "flex", "alignItems": "center"}))

    return html.Div([form, html.Div(rows, id="alerts-list")])


# ---------- Crypto ----------
CRYPTO_TICKERS = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "XRP": "XRP-USD",
    "BNB": "BNB-USD",
    "Cardano": "ADA-USD",
    "Avalanche": "AVAX-USD",
    "Dogecoin": "DOGE-USD",
    "Chainlink": "LINK-USD",
    "Polkadot": "DOT-USD",
    "Polygon": "MATIC-USD",
    "Litecoin": "LTC-USD",
}


def get_crypto_prices():
    symbols = list(CRYPTO_TICKERS.values())
    results = {}
    try:
        data = yf.download(symbols, period="2d", progress=False, group_by="ticker")
        for name, sym in CRYPTO_TICKERS.items():
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    pct = ((curr - prev) / prev) * 100
                    results[name] = (sym, curr, pct)
            except Exception:
                continue
    except Exception:
        pass
    return results


def crypto_tab():
    prices = get_crypto_prices()

    # Price cards
    cards = []
    for name, (sym, price, pct) in prices.items():
        color = COLORS["green"] if pct >= 0 else COLORS["red"]
        arrow = "▲" if pct >= 0 else "▼"
        price_str = f"${price:,.2f}" if price > 1 else f"${price:.4f}"
        cards.append(html.Div([
            html.Div(name, style={"color": COLORS["text3"], "fontSize": "10px",
                                  "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(price_str, style={"color": COLORS["text"], "fontSize": "16px",
                                       "fontWeight": "700", "fontFamily": FONT_MONO,
                                       "margin": "4px 0 2px"}),
            html.Div(f"{arrow} {pct:+.2f}%", style={"color": color, "fontSize": "12px",
                                                     "fontWeight": "700"}),
        ],
        id={"type": "crypto-card", "sym": sym},
        n_clicks=0,
        style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
               "borderRadius": "10px", "padding": "14px 16px", "cursor": "pointer",
               "transition": "border-color .15s ease"}))

    cards_grid = html.Div(cards, style={"display": "grid",
                                         "gridTemplateColumns": "repeat(4, 1fr)",
                                         "gap": "10px", "marginBottom": "20px"})

    # Treemap
    import plotly.graph_objects as go
    # Parallel crypto market cap
    crypto_syms = list(prices.keys())
    if _FAST_FETCH:
        crypto_info = fetch_many_info([v[0] for v in prices.values()], max_workers=8)
    else:
        crypto_info = {}
    labels, parents, values, colors, texts = ["Crypto"], [""], [0], [0], [""]
    for name, (sym, price, pct) in prices.items():
        try:
            market_cap = crypto_info.get(sym, {}).get("marketCap", 0) or 1e9
        except Exception:
            market_cap = 1e9
        labels.append(name)
        parents.append("Crypto")
        values.append(market_cap / 1e9)
        colors.append(pct)
        texts.append(f"{pct:+.2f}%")

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors,
                    colorscale=[[0, "#7f1d1d"], [0.25, "#dc2626"], [0.5, "#1f2937"],
                                [0.75, "#16a34a"], [1, "#14532d"]],
                    cmid=0, cmin=-5, cmax=5, line=dict(width=2, color="#080c12")),
        text=texts, textinfo="label+text", textposition="middle center",
        textfont=dict(size=14, color="#ffffff", family=FONT_MONO), tiling=dict(pad=1),
        hovertemplate="<b>%{label}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(paper_bgcolor=COLORS["bg"], margin=dict(l=0, r=0, t=0, b=0),
                      height=400, font=dict(family=FONT_MONO))

    treemap_card = html.Div([
        html.Div("CRYPTO MARKET MAP", style={"color": COLORS["text3"], "fontSize": "11px",
                                             "fontWeight": "600", "marginBottom": "10px"}),
        dcc.Graph(figure=fig, id="crypto-treemap-graph", config={"displayModeBar": False}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "16px 20px"})

    return html.Div([cards_grid, treemap_card])


# ---------- Bot Control Panel ----------
BOT_CONFIG_FILE = os.path.expanduser("~/tradingbot/config/bot_config.json")
BOT_STATUS_FILE = os.path.expanduser("~/tradingbot/config/bot_status.json")
BOT_LOG_FILE = os.path.expanduser("~/tradingbot/config/bot_log.json")


def load_bot_config():
    try:
        if os.path.exists(BOT_CONFIG_FILE):
            with open(BOT_CONFIG_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return {"active": False, "strategy": "moderate", "rebalance_frequency": "weekly",
            "drift_threshold": 5.0, "max_position_size": 40.0,
            "target_allocation": {}, "universe": [], "schwab_connected": False}


def save_bot_config(config):
    from datetime import datetime
    config["last_updated"] = datetime.now().isoformat()
    try:
        with open(BOT_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def load_bot_log():
    try:
        if os.path.exists(BOT_LOG_FILE):
            with open(BOT_LOG_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def live_allocation_card():
    """
    Live allocation panel -- shows what the bot would hold RIGHT NOW,
    computed instantly from the market-implied dial. No SVI lag.
    """
    try:
        import sys
        sys.path.insert(0, os.path.expanduser("~/tradingbot/engine"))
        from live_allocation import get_live_allocation, read_allocation_log
        alloc = get_live_allocation()
        log_entries = read_allocation_log(20)
        error = None
    except Exception as e:
        alloc = None
        log_entries = []
        error = str(e)

    if error:
        return html.Div([
            html.Div("LIVE ALLOCATION", style={"color": COLORS["text3"], "fontSize": "11px",
                                               "fontWeight": "600", "letterSpacing": "0.5px",
                                               "marginBottom": "16px"}),
            html.Div(f"Unable to compute: {error}",
                     style={"color": COLORS["red"], "fontSize": "12px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    dial = alloc["dial"]
    label = alloc["scenario_label"]
    label_colors = {
        "bull_calm": "#4ade80",
        "bull_late": "#a3e635",
        "stress":    "#f59e0b",
        "crisis":    "#f87171",
    }
    label_color = label_colors.get(label, COLORS["text2"])

    # Dial gauge bar
    dial_pct = min(max(dial * 100, 0), 100)
    gauge = html.Div([
        html.Div(style={
            "height": "8px", "borderRadius": "4px", "position": "relative",
            "background": "linear-gradient(to right, #4ade80 0%, #a3e635 28%, "
                          "#f59e0b 48%, #f97316 68%, #f87171 100%)",
        }),
        html.Div(style={
            "position": "relative", "top": "-14px",
            "left": f"calc({dial_pct}% - 6px)",
            "width": "0", "height": "0",
            "borderLeft": "6px solid transparent",
            "borderRight": "6px solid transparent",
            "borderTop": f"8px solid {COLORS['text']}",
        }),
    ], style={"marginBottom": "4px"})

    def alloc_row(name, pct, color):
        return html.Div([
            html.Span(name, style={"color": COLORS["text2"], "fontSize": "12px",
                                   "minWidth": "90px", "display": "inline-block"}),
            html.Div(
                html.Div(style={"width": f"{min(pct,100)}%", "background": color,
                                "height": "8px", "borderRadius": "4px"}),
                style={"flex": "1", "background": COLORS["border"],
                       "borderRadius": "4px", "height": "8px", "margin": "0 12px"}
            ),
            html.Span(f"{pct:.1f}%", style={"color": COLORS["text"], "fontFamily": FONT_MONO,
                                            "fontSize": "12px", "minWidth": "44px",
                                            "textAlign": "right"}),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "8px"})

    rows = [
        alloc_row("Equity", alloc["equity_pct"], "#4b8bf5"),
        alloc_row("Defensive", alloc["defensive_pct"], "#94a3b8"),
        alloc_row("DBMF", alloc["dbmf_pct"], "#a78bfa"),
        alloc_row("Gold (min)", alloc["gld_min_pct"], "#facc15"),
    ]
    for short_name, short_pct in alloc.get("shorts", {}).items():
        rows.append(alloc_row(f"Short: {short_name}", short_pct, "#f87171"))

    return html.Div([
        html.Div([
            html.Div("LIVE ALLOCATION", style={"color": COLORS["text3"], "fontSize": "11px",
                                               "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(f"as of {alloc['as_of']}", style={"color": COLORS["text3"],
                     "fontSize": "10px"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "16px"}),

        html.Div([
            html.Span(f"{dial:.3f}", style={"color": label_color, "fontSize": "28px",
                                            "fontWeight": "800", "fontFamily": FONT_MONO,
                                            "marginRight": "12px"}),
            html.Span(label.replace("_", " ").upper(),
                     style={"color": label_color, "fontSize": "13px",
                            "fontWeight": "700", "letterSpacing": "0.5px"}),
        ], style={"marginBottom": "8px"}),
        gauge,
        html.Div(style={"height": "16px"}),

        html.Div(rows),

        html.Div(style={"height": "12px"}),
        html.Div(alloc.get("summary", ""),
                 style={"color": COLORS["text2"], "fontSize": "12px",
                        "fontStyle": "italic", "marginBottom": "10px",
                        "lineHeight": "1.5"}),
        html.Div([
            html.Div(line, style={"color": COLORS["text3"], "fontSize": "11px",
                                  "padding": "4px 0", "lineHeight": "1.4"})
            for line in alloc.get("reasoning", [])
        ], style={"borderTop": f"1px solid {COLORS['border']}", "paddingTop": "10px",
                  "marginBottom": "12px"}),

        html.Div([
            html.Span("Leverage: ", style={"color": COLORS["text3"], "fontSize": "11px"}),
            html.Span(f"{alloc['leverage']:.2f}x", style={"color": COLORS["text"],
                     "fontSize": "11px", "fontFamily": FONT_MONO, "marginRight": "16px"}),
            html.Span("Computed: ", style={"color": COLORS["text3"], "fontSize": "11px"}),
            html.Span(alloc["computed_at"], style={"color": COLORS["text3"], "fontSize": "11px",
                     "fontFamily": FONT_MONO}),
        ], style={"marginTop": "4px", "marginBottom": "16px"}),

        html.Div("LOG HISTORY", style={"color": COLORS["text3"], "fontSize": "10px",
                 "fontWeight": "600", "letterSpacing": "0.5px", "marginBottom": "8px",
                 "borderTop": f"1px solid {COLORS['border']}", "paddingTop": "12px"}),
        html.Div([
            html.Div(entry, style={"color": COLORS["text3"], "fontSize": "10px",
                     "fontFamily": FONT_MONO, "padding": "3px 0", "lineHeight": "1.4",
                     "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"})
            for entry in log_entries
        ] if log_entries else [
            html.Div("No history yet -- entries accumulate as this tab is viewed.",
                     style={"color": COLORS["text3"], "fontSize": "11px", "fontStyle": "italic"})
        ], style={"maxHeight": "220px", "overflowY": "auto"}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})


def _build_liveruns_log_content():
    """
    Shared logic for building the log panel + status text.
    Used both on initial tab render and on the 60s refresh
    callback, so the two never drift out of sync with each other.
    """
    import sys
    sys.path.insert(0, os.path.expanduser("~/tradingbot/engine"))
    from backtest_reader import list_available_backtests, parse_live_log

    available = list_available_backtests()
    running_logs = [b for b in available if b["type"] == "running"]

    if running_logs:
        active_log = running_logs[0]["name"]
        records = parse_live_log(active_log, max_points=1200)
        status_text = f"● LIVE -- {active_log}"
        status_color = COLORS["green"]
    elif available:
        logs_only = [b for b in available if b["type"] in ("log", "running")]
        if logs_only:
            active_log = sorted(logs_only, key=lambda x: x["modified"])[-1]["name"]
            records = parse_live_log(active_log, max_points=1200)
            status_text = f"○ Not running -- last log: {active_log}"
            status_color = COLORS["text3"]
        else:
            records = []
            status_text, status_color = "No backtest logs found", COLORS["text3"]
    else:
        records = []
        status_text, status_color = "No backtest data found", COLORS["text3"]

    log_children = [
        html.Div(
            f"{r['date']}  ${r['value']:>10,.0f}  dial={r['dial']:.3f}  [{r['scenario']}]",
            style={"color": COLORS["text3"], "fontSize": "11px",
                   "fontFamily": FONT_MONO, "padding": "2px 0", "whiteSpace": "pre"})
        for r in reversed(records[-100:])
    ] if records else [
        html.Div("No log data yet.", style={"color": COLORS["text3"],
                 "fontSize": "11px", "fontStyle": "italic"})
    ]


    if records:
        dates = [r["date"] for r in records]
        values = [r["value"] for r in records]
        dials = [r["dial"] for r in records]
        chart = dcc.Graph(
            figure={
                "data": [
                    {"x": dates, "y": values, "type": "scatter", "mode": "lines",
                     "name": "Portfolio Value", "yaxis": "y",
                     "line": {"color": COLORS["blue"], "width": 1.5}},
                    {"x": dates, "y": dials, "type": "scatter", "mode": "lines",
                     "name": "Dial", "yaxis": "y2",
                     "line": {"color": "#f59e0b", "width": 1}},
                ],
                "layout": {
                    "height": 340,
                    "margin": {"l": 60, "r": 60, "t": 20, "b": 40},
                    "paper_bgcolor": COLORS["panel"],
                    "plot_bgcolor": COLORS["panel"],
                    "font": {"color": COLORS["text2"], "size": 11},
                    "xaxis": {"gridcolor": COLORS["border"]},
                    "yaxis": {"title": "Portfolio $", "gridcolor": COLORS["border"]},
                    "yaxis2": {"title": "Dial", "overlaying": "y", "side": "right",
                              "range": [0, 1], "gridcolor": COLORS["border"]},
                    "legend": {"orientation": "h", "y": 1.1},
                },
            },
            config={"displayModeBar": False},
            id="liveruns-chart",
        )
        latest = records[-1]
        latest_summary = html.Div([
            html.Span("Latest: " + latest["date"] + "  ", style={"color": COLORS["text2"]}),
            html.Span(f"${latest['value']:,.0f}  ", style={"color": COLORS["text"],
                     "fontWeight": "700", "fontFamily": FONT_MONO}),
            html.Span(f"dial={latest['dial']:.3f}  ", style={"color": "#f59e0b",
                     "fontFamily": FONT_MONO}),
            html.Span("[" + latest["scenario"] + "]", style={"color": COLORS["text2"]}),
        ], style={"fontSize": "13px", "marginBottom": "12px"})
    else:
        chart = html.Div("No data to chart yet.",
                          style={"color": COLORS["text3"], "padding": "40px",
                                "textAlign": "center"})
        latest_summary = html.Div()

    return records, log_children, status_text, status_color, chart, latest_summary


def backtest_viewer_tab():
    """
    Live-updating view of backtest progress, plus a picker for
    saved/completed backtest results. Read-only -- never touches
    the running backtest process itself.

    Delegates all data-building to _build_liveruns_log_content()
    so the initial render and the 60s refresh callback always
    produce identical chart/log/status content -- no duplicate
    logic to drift out of sync.
    """
    import sys
    sys.path.insert(0, os.path.expanduser("~/tradingbot/engine"))
    from backtest_reader import list_available_backtests

    records, log_children, status_text, status_color, chart, latest_summary = \
        _build_liveruns_log_content()

    available = list_available_backtests()

    picker_rows = []
    for bt in sorted(available, key=lambda x: x["modified"], reverse=True):
        final_str = f"${bt['final']:,.0f}" if bt.get("final") else "--"
        sharpe_str = f"{bt['sharpe']:.2f}" if bt.get("sharpe") else "--"
        type_color = {"running": COLORS["green"], "completed": COLORS["blue"],
                      "log": COLORS["text3"]}.get(bt["type"], COLORS["text3"])
        picker_rows.append(html.Div([
            html.Span(bt["type"].upper(), style={"color": type_color, "fontSize": "9px",
                     "fontWeight": "700", "minWidth": "70px", "display": "inline-block"}),
            html.Span(bt["name"], style={"color": COLORS["text"], "fontSize": "12px",
                     "fontFamily": FONT_MONO, "minWidth": "260px", "display": "inline-block"}),
            html.Span(final_str, style={"color": COLORS["text2"], "fontSize": "12px",
                     "minWidth": "90px", "display": "inline-block"}),
            html.Span(f"Sharpe {sharpe_str}", style={"color": COLORS["text2"], "fontSize": "12px",
                     "minWidth": "100px", "display": "inline-block"}),
            html.Span(bt["modified"], style={"color": COLORS["text3"], "fontSize": "11px"}),
        ], style={"padding": "6px 0", "borderBottom": f"1px solid {COLORS['border']}"}))

    return html.Div([
        html.Div([
            html.Div("BACKTEST VIEWER", style={"color": COLORS["text3"], "fontSize": "11px",
                     "fontWeight": "600", "letterSpacing": "0.5px"}),
            html.Div(status_text, id="liveruns-status", style={"color": status_color,
                     "fontSize": "12px", "fontWeight": "700"}),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "marginBottom": "12px"}),
        html.Div(latest_summary, id="liveruns-latest-wrapper"),
        html.Div(chart, id="liveruns-chart-wrapper"),

        html.Div(style={"height": "20px"}),
        html.Div("LIVE LOG", style={"color": COLORS["text3"], "fontSize": "10px",
                 "fontWeight": "600", "letterSpacing": "0.5px", "marginBottom": "8px",
                 "borderTop": f"1px solid {COLORS['border']}", "paddingTop": "12px"}),
        html.Div(log_children, id="liveruns-log-panel",
                 style={"maxHeight": "320px", "overflowY": "auto",
                        "background": COLORS["panel2"], "borderRadius": "6px",
                        "padding": "10px"}),

        html.Div(style={"height": "20px"}),
        html.Div("SAVED / AVAILABLE BACKTESTS", style={"color": COLORS["text3"],
                 "fontSize": "10px", "fontWeight": "600", "letterSpacing": "0.5px",
                 "marginBottom": "8px", "borderTop": f"1px solid {COLORS['border']}",
                 "paddingTop": "12px"}),
        html.Div(picker_rows if picker_rows else
                 html.Div("No backtests found.", style={"color": COLORS["text3"]})),

        html.Div(style={"height": "16px"}),
        html.Div([
            dbc.Input(id="snapshot-name-input", placeholder="Name this run to save it permanently...",
                     size="sm", style={"background": COLORS["panel2"],
                     "border": f"1px solid {COLORS['border2']}", "color": COLORS["text"],
                     "display": "inline-block", "width": "280px", "marginRight": "8px"}),
            dbc.Button("Save Snapshot", id="btn-save-snapshot", color="primary", size="sm"),
        ]),
        html.Div(id="snapshot-save-status", style={"color": COLORS["text3"],
                 "fontSize": "11px", "marginTop": "8px"}),

        dcc.Interval(id="backtest-viewer-refresh", interval=15000, n_intervals=0),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})


def bot_control_tab():
    config = load_bot_config()
    status = {}
    try:
        if os.path.exists(BOT_STATUS_FILE):
            with open(BOT_STATUS_FILE) as f:
                status = json.load(f)
    except Exception:
        pass

    is_active = config.get("active", False)
    is_connected = config.get("schwab_connected", False)
    status_color = COLORS["green"] if is_active else COLORS["red"]
    schwab_color = COLORS["green"] if is_connected else COLORS["text3"]

    # ---- Phase Indicator ----
    mode = config.get("mode", "paper")
    phase = config.get("phase", 1)
    paper_value = config.get("paper_value", 100000)
    paper_budget = config.get("paper_budget", 100000)
    paper_pnl = paper_value - paper_budget
    paper_pnl_pct = (paper_pnl / paper_budget * 100) if paper_budget else 0

    PHASES = [
        ("1", "Historical Backtesting", "Validate each model against historical data to find what works in which market regime.", "#4b8bf5"),
        ("2", "Paper Trading", "Run live with fake money. Real prices, real decisions, simulated trades. Validate before risking real capital.", "#f59e0b"),
        ("3", "Live Trading", "Real money via Schwab API. Only activated after paper trading proves the strategy.", "#4ade80"),
    ]

    phase_indicators = []
    for num, title, desc, color in PHASES:
        is_current = str(phase) == num
        phase_indicators.append(html.Div([
            html.Div(num, style={"width": "32px", "height": "32px", "borderRadius": "50%",
                                 "background": color if is_current else COLORS["panel2"],
                                 "color": "#fff" if is_current else COLORS["text3"],
                                 "display": "flex", "alignItems": "center", "justifyContent": "center",
                                 "fontWeight": "800", "fontSize": "14px", "marginBottom": "8px"}),
            html.Div(title, style={"color": color if is_current else COLORS["text2"],
                                   "fontWeight": "700" if is_current else "400",
                                   "fontSize": "13px", "marginBottom": "4px"}),
            html.Div(desc, style={"color": COLORS["text3"], "fontSize": "11px", "lineHeight": "1.5"}),
        ], style={"flex": "1", "padding": "16px",
                  "background": COLORS["panel2"] if is_current else COLORS["panel"],
                  "border": f"1px solid {color if is_current else COLORS['border']}",
                  "borderRadius": "8px", "marginRight": "12px" if num != "3" else "0",
                  "opacity": "1" if is_current else "0.6"}))

    phase_card = html.Div([
        html.Div("TRADING PHASE", style={"color": COLORS["text3"], "fontSize": "11px",
                                         "fontWeight": "600", "letterSpacing": "0.5px",
                                         "marginBottom": "16px"}),
        html.Div(phase_indicators, style={"display": "flex", "marginBottom": "16px"}),
        html.Div([
            dbc.Button("◀ Previous Phase", id="bot-phase-back", color="secondary",
                       size="sm", outline=True, className="me-2", disabled=(phase <= 1)),
            dbc.Button("Next Phase ▶", id="bot-phase-next", color="primary",
                       size="sm", disabled=(phase >= 3 or (phase == 2 and paper_pnl_pct < 5))),
            html.Span(
                f"  Complete Phase 2 with +5% paper returns to unlock Live Trading" if phase == 2 and paper_pnl_pct < 5 else "",
                style={"color": COLORS["text3"], "fontSize": "11px", "marginLeft": "12px"}
            ),
        ]),
        # Paper trading P&L if in phase 2
        html.Div([
            html.Hr(style={"borderColor": COLORS["border"]}),
            html.Div("PAPER TRADING PERFORMANCE", style={"color": COLORS["text3"],
                     "fontSize": "11px", "fontWeight": "600", "marginBottom": "12px"}),
            html.Div([
                html.Div([
                    html.Div("Paper Portfolio Value", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div(f"${paper_value:,.2f}", style={"color": COLORS["text"], "fontSize": "20px",
                                                             "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Starting Budget", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div(f"${paper_budget:,.2f}", style={"color": COLORS["text2"], "fontSize": "20px",
                                                              "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Paper P&L", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div(f"${paper_pnl:+,.2f} ({paper_pnl_pct:+.2f}%)",
                             style={"color": COLORS["green"] if paper_pnl >= 0 else COLORS["red"],
                                    "fontSize": "20px", "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Target to Unlock Live", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div("+5.00%", style={"color": COLORS["amber"], "fontSize": "20px",
                                              "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "12px"}),
        ]) if phase == 2 else html.Div(),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Phase Indicator ----
    mode = config.get("mode", "paper")
    phase = config.get("phase", 1)
    paper_value = config.get("paper_value", 100000)
    paper_budget = config.get("paper_budget", 100000)
    paper_pnl = paper_value - paper_budget
    paper_pnl_pct = (paper_pnl / paper_budget * 100) if paper_budget else 0

    PHASES = [
        ("1", "Historical Backtesting", "Validate each model against historical data to find what works in which market regime.", "#4b8bf5"),
        ("2", "Paper Trading", "Run live with fake money. Real prices, real decisions, simulated trades. Validate before risking real capital.", "#f59e0b"),
        ("3", "Live Trading", "Real money via Schwab API. Only activated after paper trading proves the strategy.", "#4ade80"),
    ]

    phase_indicators = []
    for num, title, desc, color in PHASES:
        is_current = str(phase) == num
        phase_indicators.append(html.Div([
            html.Div(num, style={"width": "32px", "height": "32px", "borderRadius": "50%",
                                 "background": color if is_current else COLORS["panel2"],
                                 "color": "#fff" if is_current else COLORS["text3"],
                                 "display": "flex", "alignItems": "center", "justifyContent": "center",
                                 "fontWeight": "800", "fontSize": "14px", "marginBottom": "8px"}),
            html.Div(title, style={"color": color if is_current else COLORS["text2"],
                                   "fontWeight": "700" if is_current else "400",
                                   "fontSize": "13px", "marginBottom": "4px"}),
            html.Div(desc, style={"color": COLORS["text3"], "fontSize": "11px", "lineHeight": "1.5"}),
        ], style={"flex": "1", "padding": "16px",
                  "background": COLORS["panel2"] if is_current else COLORS["panel"],
                  "border": f"1px solid {color if is_current else COLORS['border']}",
                  "borderRadius": "8px", "marginRight": "12px" if num != "3" else "0",
                  "opacity": "1" if is_current else "0.6"}))

    phase_card = html.Div([
        html.Div("TRADING PHASE", style={"color": COLORS["text3"], "fontSize": "11px",
                                         "fontWeight": "600", "letterSpacing": "0.5px",
                                         "marginBottom": "16px"}),
        html.Div(phase_indicators, style={"display": "flex", "marginBottom": "16px"}),
        html.Div([
            dbc.Button("◀ Previous Phase", id="bot-phase-back", color="secondary",
                       size="sm", outline=True, className="me-2", disabled=(phase <= 1)),
            dbc.Button("Next Phase ▶", id="bot-phase-next", color="primary",
                       size="sm", disabled=(phase >= 3 or (phase == 2 and paper_pnl_pct < 5))),
            html.Span(
                f"  Complete Phase 2 with +5% paper returns to unlock Live Trading" if phase == 2 and paper_pnl_pct < 5 else "",
                style={"color": COLORS["text3"], "fontSize": "11px", "marginLeft": "12px"}
            ),
        ]),
        # Paper trading P&L if in phase 2
        html.Div([
            html.Hr(style={"borderColor": COLORS["border"]}),
            html.Div("PAPER TRADING PERFORMANCE", style={"color": COLORS["text3"],
                     "fontSize": "11px", "fontWeight": "600", "marginBottom": "12px"}),
            html.Div([
                html.Div([
                    html.Div("Paper Portfolio Value", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div(f"${paper_value:,.2f}", style={"color": COLORS["text"], "fontSize": "20px",
                                                             "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Starting Budget", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div(f"${paper_budget:,.2f}", style={"color": COLORS["text2"], "fontSize": "20px",
                                                              "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Paper P&L", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div(f"${paper_pnl:+,.2f} ({paper_pnl_pct:+.2f}%)",
                             style={"color": COLORS["green"] if paper_pnl >= 0 else COLORS["red"],
                                    "fontSize": "20px", "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("Target to Unlock Live", style={"color": COLORS["text3"], "fontSize": "11px"}),
                    html.Div("+5.00%", style={"color": COLORS["amber"], "fontSize": "20px",
                                              "fontWeight": "800", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "12px"}),
        ]) if phase == 2 else html.Div(),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Status Header ----
    header = html.Div([
        html.Div([
            html.Div([
                html.Div("● RUNNING" if is_active else "● STOPPED",
                         style={"color": status_color, "fontSize": "20px", "fontWeight": "800"}),
                html.Div("● Schwab Connected" if is_connected else "● Schwab Not Connected",
                         style={"color": schwab_color, "fontSize": "12px", "marginTop": "4px"}),
                html.Div(f"Last rebalance: {status.get('last_rebalance', 'Never')}",
                         style={"color": COLORS["text3"], "fontSize": "12px", "marginTop": "4px"}),
                html.Div(f"Next rebalance: {status.get('next_rebalance', 'N/A')}",
                         style={"color": COLORS["text3"], "fontSize": "12px"}),
            ], style={"flex": "1"}),
            html.Div([
                dbc.Button("▶ START", id="bot-start-btn", color="success",
                           size="lg", className="me-3", disabled=is_active),
                dbc.Button("■ STOP", id="bot-stop-btn", color="danger",
                           size="lg", disabled=not is_active),
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={"background": COLORS["panel"], "border": f"2px solid {status_color}",
              "borderRadius": "12px", "padding": "24px", "marginBottom": "20px"})

    # ---- Market Regime ----
    regime = config.get("market_regime") or status.get("market_regime", "Unknown")
    active_model = config.get("active_model") or status.get("active_model", "Waiting...")
    confidence = config.get("model_confidence") or status.get("model_confidence")

    REGIME_COLORS = {
        "bull": COLORS["green"], "recovery": "#86efac",
        "bear": COLORS["red"], "crisis": "#dc2626",
        "volatile": COLORS["amber"], "stable": COLORS["blue"],
        "trending": "#38bdf8", "uncertain": COLORS["text3"],
        "Unknown": COLORS["text3"], "Waiting...": COLORS["text3"],
    }
    regime_color = REGIME_COLORS.get(regime, COLORS["text3"])

    MODEL_INFO = {
        "black_litterman_mcmc": ("Black-Litterman + MCMC", "#4b8bf5",
                                 "Bayesian portfolio optimization combining market equilibrium priors with AI sentiment views. Best in normal/bull markets."),
        "mean_variance": ("Mean-Variance (Markowitz)", "#4ade80",
                         "Classic modern portfolio theory. Maximizes return for given risk level. Best in stable, low-volatility regimes."),
        "risk_parity": ("Risk Parity", "#f59e0b",
                       "Equal risk contribution from each asset. Protects against concentration risk. Best in volatile or uncertain markets."),
        "momentum": ("Momentum", "#38bdf8",
                    "Trend-following strategy. Overweights recent winners. Best in strong trending bull or bear markets."),
        "minimum_variance": ("Minimum Variance", "#a78bfa",
                            "Pure risk minimization. Finds lowest-volatility portfolio. Best in crisis or high-correlation regimes."),
        "equal_weight": ("Equal Weight", "#94a3b8",
                        "Simple equal allocation across all assets. Fallback when no model has high confidence."),
        "Waiting...": ("Waiting for engine...", COLORS["text3"], "Engine not yet started."),
    }
    model_name, model_color, model_desc = MODEL_INFO.get(active_model,
        ("Unknown", COLORS["text3"], ""))

    regime_card = html.Div([
        html.Div("MARKET INTELLIGENCE", style={"color": COLORS["text3"], "fontSize": "11px",
                                               "fontWeight": "600", "letterSpacing": "0.5px",
                                               "marginBottom": "16px"}),
        html.Div([
            # Regime
            html.Div([
                html.Div("DETECTED REGIME", style={"color": COLORS["text3"], "fontSize": "10px",
                                                   "fontWeight": "600", "letterSpacing": "0.5px"}),
                html.Div(regime.upper(), style={"color": regime_color, "fontSize": "22px",
                                                "fontWeight": "800", "fontFamily": FONT_MONO,
                                                "margin": "6px 0"}),
                html.Div("Market environment classification based on VIX, yield curve, momentum and correlation signals.",
                         style={"color": COLORS["text3"], "fontSize": "11px", "lineHeight": "1.5"}),
            ], style={"flex": "1", "padding": "16px", "background": COLORS["panel2"],
                      "borderRadius": "8px", "borderLeft": f"3px solid {regime_color}",
                      "marginRight": "12px"}),
            # Active model
            html.Div([
                html.Div("ACTIVE MODEL", style={"color": COLORS["text3"], "fontSize": "10px",
                                               "fontWeight": "600", "letterSpacing": "0.5px"}),
                html.Div(model_name, style={"color": model_color, "fontSize": "16px",
                                            "fontWeight": "800", "margin": "6px 0",
                                            "lineHeight": "1.2"}),
                html.Div(model_desc, style={"color": COLORS["text3"], "fontSize": "11px",
                                            "lineHeight": "1.5"}),
            ], style={"flex": "2", "padding": "16px", "background": COLORS["panel2"],
                      "borderRadius": "8px", "borderLeft": f"3px solid {model_color}",
                      "marginRight": "12px"}),
            # Confidence
            html.Div([
                html.Div("MODEL CONFIDENCE", style={"color": COLORS["text3"], "fontSize": "10px",
                                                   "fontWeight": "600", "letterSpacing": "0.5px"}),
                html.Div(f"{confidence:.0f}%" if confidence else "N/A",
                         style={"color": COLORS["blue"] if confidence and confidence > 70
                                else COLORS["amber"] if confidence else COLORS["text3"],
                                "fontSize": "28px", "fontWeight": "800",
                                "fontFamily": FONT_MONO, "margin": "6px 0"}),
                html.Div("MCMC posterior confidence in current allocation.",
                         style={"color": COLORS["text3"], "fontSize": "11px"}),
            ], style={"flex": "1", "padding": "16px", "background": COLORS["panel2"],
                      "borderRadius": "8px"}),
        ], style={"display": "flex"}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Model Roster ----
    models_config = config.get("models", {})
    model_rows = []
    for model_id, info in MODEL_INFO.items():
        if model_id == "Waiting...":
            continue
        mname, mcolor, mdesc = info
        enabled = models_config.get(model_id, {}).get("enabled", True)
        regimes = models_config.get(model_id, {}).get("regimes", [])
        is_active_model = model_id == active_model
        model_rows.append(html.Div([
            html.Div([
                html.Div(mname, style={"color": mcolor if is_active_model else COLORS["text"],
                                       "fontWeight": "700", "fontSize": "13px"}),
                html.Div(f"Active in: {', '.join(regimes)}",
                         style={"color": COLORS["text3"], "fontSize": "11px", "marginTop": "2px"}),
            ], style={"flex": "1"}),
            html.Div("● ACTIVE" if is_active_model else "",
                     style={"color": mcolor, "fontSize": "11px", "fontWeight": "700",
                            "marginRight": "16px"}),
            dbc.Switch(id={"type": "model-toggle", "index": model_id},
                       value=enabled, className="ms-2"),
        ], style={"display": "flex", "alignItems": "center", "padding": "12px 16px",
                  "background": COLORS["panel2"] if is_active_model else COLORS["panel"],
                  "border": f"1px solid {mcolor if is_active_model else COLORS['border']}",
                  "borderRadius": "8px", "marginBottom": "6px"}))

    models_card = html.Div([
        html.Div("STRATEGY ENGINE — MODEL ROSTER", style={"color": COLORS["text3"],
                 "fontSize": "11px", "fontWeight": "600", "letterSpacing": "0.5px",
                 "marginBottom": "4px"}),
        html.Div("The bot autonomously selects the best model for current market conditions. Toggle models on/off to include/exclude them from the selection pool.",
                 style={"color": COLORS["text3"], "fontSize": "11px", "marginBottom": "16px"}),
        html.Div(model_rows),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Basic Config ----
    settings_card = html.Div([
        html.Div("INVESTMENT PARAMETERS", style={"color": COLORS["text3"], "fontSize": "11px",
                                                 "fontWeight": "600", "letterSpacing": "0.5px",
                                                 "marginBottom": "16px"}),
        html.Div([
            html.Div([
                html.Div("Budget ($)", style={"color": COLORS["text2"], "fontSize": "13px",
                                              "marginBottom": "6px"}),
                dbc.Input(id="bot-budget", type="number", value=config.get("budget", 10000),
                          min=100, step=100,
                          style={"background": COLORS["panel2"],
                                 "border": f"1px solid {COLORS['border2']}",
                                 "color": COLORS["text"]}),
            ], style={"flex": "1", "marginRight": "16px"}),
            html.Div([
                html.Div("Risk Tolerance", style={"color": COLORS["text2"], "fontSize": "13px",
                                                  "marginBottom": "6px"}),
                dbc.Select(id="bot-strategy",
                           options=[{"label": "Conservative", "value": "conservative"},
                                    {"label": "Moderate", "value": "moderate"},
                                    {"label": "Aggressive", "value": "aggressive"}],
                           value=config.get("risk_tolerance", "moderate"),
                           style={"background": COLORS["panel2"],
                                  "border": f"1px solid {COLORS['border2']}",
                                  "color": COLORS["text"]}),
            ], style={"flex": "1", "marginRight": "16px"}),
            html.Div([
                html.Div("Rebalance Frequency", style={"color": COLORS["text2"], "fontSize": "13px",
                                                       "marginBottom": "6px"}),
                dbc.Select(id="bot-frequency",
                           options=[{"label": "Daily", "value": "daily"},
                                    {"label": "Weekly", "value": "weekly"},
                                    {"label": "Monthly", "value": "monthly"},
                                    {"label": "Quarterly", "value": "quarterly"}],
                           value=config.get("rebalance_frequency", "weekly"),
                           style={"background": COLORS["panel2"],
                                  "border": f"1px solid {COLORS['border2']}",
                                  "color": COLORS["text"]}),
            ], style={"flex": "1", "marginRight": "16px"}),
            html.Div([
                html.Div("Drift Threshold (%)", style={"color": COLORS["text2"], "fontSize": "13px",
                                                       "marginBottom": "6px"}),
                dbc.Input(id="bot-drift", type="number", value=config.get("drift_threshold", 5.0),
                          min=1, max=20, step=0.5,
                          style={"background": COLORS["panel2"],
                                 "border": f"1px solid {COLORS['border2']}",
                                 "color": COLORS["text"]}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "marginBottom": "16px"}),
        dbc.Button("Save Parameters", id="bot-save-btn", color="primary", size="sm"),
        html.Div(id="bot-save-status", style={"color": COLORS["green"], "fontSize": "12px",
                                               "marginTop": "8px"}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Current Allocation ----
    current_alloc = config.get("current_allocation", {})
    alloc_card = html.Div([
        html.Div("CURRENT ALLOCATION", style={"color": COLORS["text3"], "fontSize": "11px",
                                              "fontWeight": "600", "letterSpacing": "0.5px",
                                              "marginBottom": "12px"}),
        html.Div([
            html.Div([
                html.Span(sym, style={"color": COLORS["text"], "fontWeight": "700",
                                      "fontFamily": FONT_MONO, "minWidth": "80px"}),
                html.Div(html.Div(style={"width": f"{w}%", "background": COLORS["blue"],
                                         "height": "6px", "borderRadius": "3px"}),
                         style={"flex": "1", "background": COLORS["border"],
                                "borderRadius": "3px", "height": "6px", "margin": "0 16px"}),
                html.Span(f"{w:.1f}%", style={"color": COLORS["text2"], "fontFamily": FONT_MONO,
                                               "fontSize": "13px", "minWidth": "45px",
                                               "textAlign": "right"}),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"})
            for sym, w in current_alloc.items()
        ]) if current_alloc else
        html.Div("Engine not started — allocation will appear here once the bot is running.",
                 style={"color": COLORS["text3"], "fontSize": "12px", "fontStyle": "italic"}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Trade Log ----
    log = load_bot_log()
    log_rows = []
    if log:
        for entry in reversed(log[-20:]):
            action_color = COLORS["green"] if entry.get("action") == "BUY" else COLORS["red"]
            log_rows.append(html.Div([
                html.Span(entry.get("date", ""), style={"color": COLORS["text3"],
                                                         "fontSize": "11px", "minWidth": "140px"}),
                html.Span(entry.get("action", ""), style={"color": action_color,
                                                           "fontWeight": "700", "fontSize": "12px",
                                                           "minWidth": "50px"}),
                html.Span(entry.get("symbol", ""), style={"color": COLORS["text"],
                                                           "fontWeight": "700",
                                                           "fontFamily": FONT_MONO,
                                                           "minWidth": "70px"}),
                html.Span(entry.get("model", ""), style={"color": COLORS["blue"],
                                                          "fontSize": "11px", "minWidth": "160px"}),
                html.Span(entry.get("details", ""), style={"color": COLORS["text2"],
                                                            "fontSize": "12px"}),
            ], style={"display": "flex", "gap": "12px", "padding": "8px 0",
                      "borderBottom": f"1px solid {COLORS['border']}"}))
    else:
        log_rows = [html.Div("No trades yet. Start the bot to begin trading.",
                             style={"color": COLORS["text2"]})]

    log_card = html.Div([
        html.Div("TRADE LOG", style={"color": COLORS["text3"], "fontSize": "11px",
                                     "fontWeight": "600", "letterSpacing": "0.5px",
                                     "marginBottom": "12px"}),
        html.Div(log_rows),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px"})

    # Schwab connection card
    schwab_status = {}
    schwab_status_file = os.path.expanduser("~/tradingbot/config/schwab_status.json")
    try:
        if os.path.exists(schwab_status_file):
            with open(schwab_status_file) as f:
                schwab_status = json.load(f)
    except Exception:
        pass

    schwab_connected = schwab_status.get("connected", False)
    schwab_color = COLORS["green"] if schwab_connected else COLORS["red"]
    schwab_text = "● Connected" if schwab_connected else "● Not Connected"
    last_refresh = schwab_status.get("last_refresh", "Never")

    schwab_card = html.Div([
        html.Div("SCHWAB CONNECTION", style={"color": COLORS["text3"], "fontSize": "11px",
                                             "fontWeight": "600", "letterSpacing": "0.5px",
                                             "marginBottom": "16px"}),
        html.Div([
            html.Div([
                html.Div(schwab_text, style={"color": schwab_color, "fontSize": "16px",
                                             "fontWeight": "700", "marginBottom": "4px"}),
                html.Div(f"Account: {schwab_status.get('account_hash', 'N/A')}",
                         style={"color": COLORS["text2"], "fontSize": "12px"}),
                html.Div(f"Last refresh: {last_refresh[:19] if last_refresh != 'Never' else 'Never'}",
                         style={"color": COLORS["text3"], "fontSize": "12px"}),
            ], style={"flex": "1"}),
            html.Div([
                dbc.Button("Connect Schwab", id="schwab-connect-btn", color="primary",
                           size="sm", className="me-2", disabled=schwab_connected),
                dbc.Button("Sync Portfolio", id="schwab-sync-btn", color="secondary",
                           size="sm", outline=True, disabled=not schwab_connected),
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div(id="schwab-status-msg",
                 style={"color": COLORS["green"], "fontSize": "12px", "marginTop": "8px"}),
        html.Div([
            html.Hr(style={"borderColor": COLORS["border"]}),
            html.Div("Once connected, the bot can:", style={"color": COLORS["text2"],
                                                             "fontSize": "12px",
                                                             "marginBottom": "8px"}),
            html.Div([
                html.Div("✓ Auto-populate your Portfolio tab with real holdings",
                         style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "4px"}),
                html.Div("✓ Read account balance and buying power",
                         style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "4px"}),
                html.Div("✓ Execute rebalance trades automatically (Phase 3 only)",
                         style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "4px"}),
                html.Div("✓ Send hard sell alerts to Slack and lock for your authorization",
                         style={"color": COLORS["text3"], "fontSize": "12px"}),
            ]),
        ]) if not schwab_connected else html.Div(),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # Slack status card
    slack_card = html.Div([
        html.Div("SLACK NOTIFICATIONS", style={"color": COLORS["text3"], "fontSize": "11px",
                                               "fontWeight": "600", "letterSpacing": "0.5px",
                                               "marginBottom": "12px"}),
        html.Div([
            html.Div([
                html.Div("● #alerts channel connected",
                         style={"color": COLORS["green"], "fontSize": "13px",
                                "fontWeight": "600", "marginBottom": "4px"}),
                html.Div("You will receive Slack messages for price alerts, hard sells, rebalances and paper trading milestones.",
                         style={"color": COLORS["text3"], "fontSize": "12px"}),
            ], style={"flex": "1"}),
            html.Div([
                dbc.Button("Test Slack", id="slack-test-btn", color="secondary",
                           size="sm", outline=True),
                html.Div(id="slack-test-status",
                         style={"color": COLORS["green"], "fontSize": "12px", "marginTop": "6px"}),
            ]),
        ], style={"display": "flex", "alignItems": "center", "gap": "16px"}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    # ---- Global Monitor Panel ----
    import pytz
    from datetime import datetime
    ET = pytz.timezone("America/New_York")
    now_et = datetime.now(ET)
    hour = now_et.hour

    monitor_baseline = 0.41
    monitor_last_check = "Not started"
    monitor_status = "STOPPED"
    monitor_dial = 0.41
    risk_mult = 0.93

    try:
        mb = json.load(open(os.path.expanduser(
            "~/tradingbot/config/monitor_baseline.json")))
        monitor_baseline = mb.get("baseline", 0.41)
        ts = mb.get("timestamp", "")
        if ts:
            monitor_last_check = ts[:16].replace("T", " ")
        monitor_status = "RUNNING"
    except Exception:
        pass

    try:
        import pandas as pd
        stab = pd.read_parquet(os.path.expanduser(
            "~/tradingbot/engine/histdata/stability.parquet"))
        monitor_dial = float(stab["stability_risk"].dropna().iloc[-1])
        risk_mult = max(0.25, 1.0/(1.0 + max(monitor_dial-0.5,0)*8))
    except Exception:
        pass

    dial_color = (COLORS["green"] if monitor_dial < 0.40 else
                  "#f59e0b" if monitor_dial < 0.60 else
                  "#f97316" if monitor_dial < 0.75 else
                  COLORS["red"])
    status_color = COLORS["green"] if monitor_status == "RUNNING" else COLORS["text3"]

    all_sessions = [
        ("Futures",  18, 17),
        ("Asia",     20,  6),
        ("MENA",      3, 10),
        ("Europe",    3, 12),
        ("Americas",  9, 17),
    ]
    session_rows = []
    for sname, sopen, sclose in all_sessions:
        if sopen > sclose:
            is_open = hour >= sopen or hour < sclose
        else:
            is_open = sopen <= hour < sclose
        dot = "🟢" if is_open else "⚫"
        label = "OPEN" if is_open else f"opens {sopen}:00 ET"
        label_color = COLORS["green"] if is_open else COLORS["text3"]
        session_rows.append(html.Div([
            html.Span(dot, style={"marginRight": "8px"}),
            html.Span(sname, style={"fontWeight": "600", "width": "90px",
                                    "display": "inline-block", "fontSize": "13px"}),
            html.Span(label, style={"color": label_color, "fontSize": "12px"}),
        ], style={"padding": "3px 0"}))

    monitor_card = html.Div([
        html.Div("🌍  Global Market Monitor",
                 style={"fontWeight": "600", "fontSize": "15px", "marginBottom": "16px"}),

        html.Div([
            html.Div([
                html.Div("Status", style={"fontSize": "11px", "color": COLORS["text3"], "marginBottom": "4px"}),
                html.Div([
                    html.Span("● ", style={"color": status_color}),
                    html.Span(monitor_status, style={"fontWeight": "600"}),
                ]),
            ], style={"flex": "1"}),
            html.Div([
                html.Div("Dial", style={"fontSize": "11px", "color": COLORS["text3"], "marginBottom": "4px"}),
                html.Div(f"{monitor_dial:.2f}",
                         style={"fontWeight": "700", "fontSize": "24px", "color": dial_color}),
            ], style={"flex": "1"}),
            html.Div([
                html.Div("Risk Mult", style={"fontSize": "11px", "color": COLORS["text3"], "marginBottom": "4px"}),
                html.Div(f"{risk_mult:.2f}",
                         style={"fontWeight": "700", "fontSize": "24px"}),
            ], style={"flex": "1"}),
            html.Div([
                html.Div("Baseline", style={"fontSize": "11px", "color": COLORS["text3"], "marginBottom": "4px"}),
                html.Div(f"{monitor_baseline:.2f}",
                         style={"fontWeight": "700", "fontSize": "24px"}),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "16px"}),

        html.Div([
            html.Div(style={
                "height": "6px", "borderRadius": "3px",
                "background": "linear-gradient(to right, #22c55e 0%, #f59e0b 50%, #ef4444 100%)",
                "marginBottom": "2px",
            }),
            html.Div([
                html.Span("▲", style={
                    "position": "relative",
                    "left": f"calc({monitor_dial*100:.0f}% - 6px)",
                    "color": dial_color, "fontSize": "10px",
                }),
            ]),
        ], style={"marginBottom": "16px"}),

        html.Div("Market Sessions",
                 style={"fontSize": "12px", "color": COLORS["text3"],
                        "fontWeight": "600", "marginBottom": "8px"}),
        html.Div(session_rows, style={"marginBottom": "16px"}),

        html.Div([
            html.Span("Last check: ", style={"color": COLORS["text3"], "fontSize": "12px"}),
            html.Span(monitor_last_check, style={"fontSize": "12px", "marginRight": "16px"}),
            html.Span("Next rebalance: ", style={"color": COLORS["text3"], "fontSize": "12px"}),
            html.Span("Sunday 8:00pm ET", style={"fontSize": "12px"}),
        ], style={"marginBottom": "16px"}),

        html.Div([
            dbc.Button("▶ Start Monitor", id="btn-start-monitor",
                       color="success", size="sm", className="me-2"),
            dbc.Button("⏹ Stop", id="btn-stop-monitor",
                       color="secondary", size="sm", outline=True, className="me-2"),
            dbc.Button("🔔 Test Alert", id="btn-test-alert",
                       color="warning", size="sm", outline=True, className="me-2"),
            dbc.Button("📋 View Log", id="btn-monitor-log",
                       color="primary", size="sm", outline=True),
        ]),
        html.Div(id="monitor-status-msg",
                 style={"marginTop": "8px", "fontSize": "12px", "color": COLORS["text3"]}),

    ], style={"background": COLORS["panel"],
              "border": f"1px solid {COLORS['border']}",
              "borderRadius": "10px", "padding": "20px", "marginBottom": "16px"})

    return html.Div([phase_card, live_allocation_card(), header, regime_card, models_card,
                     settings_card, schwab_card, slack_card, alloc_card, log_card, monitor_card])



# ---------- Analyst Ratings ----------
def get_analyst_ratings(symbols):
    import requests
    from concurrent.futures import ThreadPoolExecutor, as_completed
    key = os.getenv("FINNHUB_API_KEY")
    results = {}

    def fetch_one(sym):
        cached = mem_get(f"rating:{sym}", ttl=3600) if _FAST_FETCH else None
        if cached:
            return sym, cached
        try:
            resp = requests.get("https://finnhub.io/api/v1/stock/recommendation",
                                params={"symbol": sym, "token": key}, timeout=10)
            data = resp.json()
            result = data[0] if data else None
            if result and _FAST_FETCH:
                mem_set(f"rating:{sym}", result)
            return sym, result
        except Exception:
            return sym, None

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_one, sym): sym for sym in symbols}
        for future in as_completed(futures):
            sym, data = future.result()
            if data:
                results[sym] = data
    return results


def get_price_targets(symbols):
    import requests
    key = os.getenv("FINNHUB_API_KEY")
    results = {}
    for sym in symbols:
        try:
            resp = requests.get("https://finnhub.io/api/v1/stock/price-target",
                                params={"symbol": sym, "token": key}, timeout=10)
            data = resp.json()
            if data.get("targetMean"):
                results[sym] = data
        except Exception:
            continue
    return results


def analyst_ratings_tab():
    # Use watchlist + portfolio symbols
    import json as _json
    def _load_wl():
        wl_file = os.path.expanduser("~/tradingbot/config/watchlist.json")
        try:
            if os.path.exists(wl_file):
                with open(wl_file) as f:
                    return _json.load(f)
        except Exception:
            pass
        return []
    wl_symbols = _load_wl()
    pf_symbols = [h["symbol"] for h in load_portfolio()]
    all_symbols = list(dict.fromkeys(wl_symbols + pf_symbols))  # dedupe, preserve order

    # Add default stocks since ETFs don't have analyst ratings
    default_stocks = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM"]
    # Filter to stocks only (ETFs don't have ratings) and add defaults
    etf_keywords = ["VTI", "VOO", "SPY", "QQQ", "VNQ", "BND", "AGG", "GLD", "SLV",
                    "XL", "ARK", "VGT", "VHT", "SCHF", "VXUS", "EEM", "IWM", "DIA"]
    stock_symbols = [s for s in all_symbols
                     if not any(s.startswith(e) or s == e for e in etf_keywords)]
    # Add defaults if no stocks in watchlist
    if not stock_symbols:
        stock_symbols = default_stocks
    else:
        # Add any missing defaults
        for s in default_stocks:
            if s not in stock_symbols:
                stock_symbols.append(s)
    all_symbols = stock_symbols[:15]  # limit to 15 to avoid rate limiting

    ratings = get_analyst_ratings(all_symbols)
    targets = get_price_targets(all_symbols)

    # Fetch current prices
    prices = {}
    for sym in all_symbols:
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if not hist.empty:
                prices[sym] = float(hist["Close"].dropna().iloc[-1])
        except Exception:
            prices[sym] = 0

    import plotly.graph_objects as go

    rows = []
    for sym in all_symbols:
        if sym not in ratings:
            continue
        r = ratings[sym]
        strong_buy = r.get("strongBuy", 0)
        buy = r.get("buy", 0)
        hold = r.get("hold", 0)
        sell = r.get("sell", 0)
        strong_sell = r.get("strongSell", 0)
        total = strong_buy + buy + hold + sell + strong_sell
        if total == 0:
            continue

        # Consensus score (1=strong sell, 5=strong buy)
        score = (strong_buy * 5 + buy * 4 + hold * 3 + sell * 2 + strong_sell * 1) / total
        if score >= 4.5:
            consensus = "Strong Buy"
            cons_color = "#16a34a"
        elif score >= 3.5:
            consensus = "Buy"
            cons_color = COLORS["green"]
        elif score >= 2.5:
            consensus = "Hold"
            cons_color = COLORS["amber"]
        elif score >= 1.5:
            consensus = "Sell"
            cons_color = COLORS["red"]
        else:
            consensus = "Strong Sell"
            cons_color = "#dc2626"

        # Price target
        pt = targets.get(sym, {})
        target_mean = pt.get("targetMean", 0)
        target_high = pt.get("targetHigh", 0)
        target_low = pt.get("targetLow", 0)
        current_price = prices.get(sym, 0)
        upside = ((target_mean - current_price) / current_price * 100) if current_price and target_mean else None

        # Rating bar
        bar_fig = go.Figure()
        categories = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]
        values = [strong_buy, buy, hold, sell, strong_sell]
        bar_colors = ["#16a34a", "#4ade80", "#f59e0b", "#f87171", "#dc2626"]
        bar_fig.add_trace(go.Bar(
            x=values, y=categories, orientation="h",
            marker_color=bar_colors,
            text=[f"{v}" for v in values],
            textposition="inside",
            textfont=dict(color="#fff", size=11),
        ))
        bar_fig.update_layout(
            paper_bgcolor=COLORS["panel2"], plot_bgcolor=COLORS["panel2"],
            font=dict(color=COLORS["text2"]),
            margin=dict(l=0, r=0, t=0, b=0), height=130,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False),
            showlegend=False,
        )

        rows.append(html.Div([
            # Header
            html.Div([
                html.Div([
                    html.Span(sym, style={"color": COLORS["text"], "fontWeight": "800",
                                          "fontSize": "18px", "fontFamily": FONT_MONO,
                                          "marginRight": "12px"}),
                    html.Span(consensus, style={"color": cons_color, "fontWeight": "700",
                                                "fontSize": "14px", "background": f"{cons_color}22",
                                                "padding": "3px 10px", "borderRadius": "6px"}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div(f"${current_price:.2f}", style={"color": COLORS["text"],
                                                              "fontSize": "16px", "fontWeight": "700",
                                                              "fontFamily": FONT_MONO,
                                                              "textAlign": "right"}),
                    html.Div(f"Target: ${target_mean:.2f}" if target_mean else "No target",
                             style={"color": COLORS["text2"], "fontSize": "12px",
                                    "textAlign": "right"}),
                    html.Div(f"Upside: {upside:+.1f}%" if upside else "",
                             style={"color": COLORS["green"] if upside and upside > 0 else COLORS["red"],
                                    "fontSize": "12px", "fontWeight": "700", "textAlign": "right"}),
                ]),
            ], style={"display": "flex", "alignItems": "flex-start", "marginBottom": "12px"}),

            # Rating bar
            html.Div([
                html.Div([
                    dcc.Graph(figure=bar_fig, config={"displayModeBar": False}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div(f"{total} analysts", style={"color": COLORS["text3"],
                                                          "fontSize": "11px", "marginBottom": "8px"}),
                    html.Div(f"High: ${target_high:.2f}" if target_high else "",
                             style={"color": COLORS["green"], "fontSize": "11px",
                                    "fontFamily": FONT_MONO}),
                    html.Div(f"Mean: ${target_mean:.2f}" if target_mean else "",
                             style={"color": COLORS["text2"], "fontSize": "11px",
                                    "fontFamily": FONT_MONO}),
                    html.Div(f"Low: ${target_low:.2f}" if target_low else "",
                             style={"color": COLORS["red"], "fontSize": "11px",
                                    "fontFamily": FONT_MONO}),
                ], style={"width": "100px", "paddingLeft": "16px"}),
            ], style={"display": "flex"}),

            html.Div(f"Period: {r.get('period', 'N/A')}",
                     style={"color": COLORS["text3"], "fontSize": "11px", "marginTop": "8px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderLeft": f"3px solid {cons_color}",
                  "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "12px"}))

    if not rows:
        return html.Div("No analyst ratings available for your tickers.",
                        style={"color": COLORS["text2"]})

    return html.Div([
        html.Div("Wall Street analyst consensus ratings and price targets for your watchlist and portfolio tickers. Updated monthly.",
                 style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"}),
        html.Div(rows),
    ])


# ---------- Dividend Tracker ----------
def dividend_tracker_tab(extra_symbols=None):
    extra_symbols = extra_symbols or []
    import pandas as pd

    # Load portfolio for real share counts
    portfolio = load_portfolio()
    pf_map = {h["symbol"]: h.get("shares", 0) for h in portfolio}

    # Load watchlist
    import json as _json
    wl_file = os.path.expanduser("~/tradingbot/config/watchlist.json")
    try:
        wl = _json.load(open(wl_file)) if os.path.exists(wl_file) else []
    except Exception:
        wl = []

    # Only show portfolio holdings by default + any extras manually added
    all_symbols = list(dict.fromkeys(list(pf_map.keys()) + extra_symbols))
    if not all_symbols:
        all_symbols = []

    # Add ticker form
    add_form = html.Div([
        html.Div("ADD TICKER", style={"color": COLORS["text3"], "fontSize": "11px",
                                      "fontWeight": "600", "letterSpacing": "0.5px",
                                      "marginBottom": "8px"}),
        html.Div([
            dbc.Input(id="div-add-input", placeholder="Add ticker (e.g. SCHD)",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "flex": "1", "marginRight": "8px"}),
            dbc.Button("Add", id="div-add-btn", color="primary", size="sm"),
        ], style={"display": "flex", "marginBottom": "20px"}),
    ])

    dividend_data = []
    for sym in all_symbols:
        try:
            t = yf.Ticker(sym)
            info = t.info
            divs = t.dividends
            yield_pct = info.get("dividendYield", 0) or 0
            rate = info.get("dividendRate", 0) or 0
            ex_date = info.get("exDividendDate")
            price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            recent_divs = divs.tail(4) if not divs.empty else None
            shares = pf_map.get(sym, 0)
            # Calculate annual income from last 12 months of dividends if rate unavailable
            if not rate and not divs.empty:
                one_year_ago = divs.index[-1] - pd.DateOffset(years=1)
                annual_divs = divs[divs.index >= one_year_ago]
                rate = float(annual_divs.sum()) if not annual_divs.empty else 0
            annual_income = rate * shares if rate and shares else 0

            if yield_pct > 0 or (recent_divs is not None and len(recent_divs) > 0):
                dividend_data.append({
                    "symbol": sym,
                    "yield": yield_pct * 100 if yield_pct < 1 else yield_pct,
                    "rate": rate,
                    "ex_date": ex_date,
                    "price": price,
                    "recent_divs": recent_divs,
                    "shares": shares,
                    "annual_income": annual_income,
                    "in_portfolio": sym in pf_map,
                })
        except Exception:
            continue

    import plotly.graph_objects as go
    if not dividend_data:
        return html.Div([add_form,
                         html.Div("Add holdings in the Portfolio tab to see your dividend income, or add tickers above.",
                                  style={"color": COLORS["text2"]})])
    from datetime import datetime

    # Summary cards
    total_income = sum(d["annual_income"] for d in dividend_data)
    avg_yield = sum(d["yield"] for d in dividend_data) / len(dividend_data) if dividend_data else 0

    summary = html.Div([
        html.Div([
            html.Div("ANNUAL DIVIDEND INCOME", style={"color": COLORS["text3"], "fontSize": "10px",
                                                       "fontWeight": "600"}),
            html.Div(f"${total_income:,.2f}", style={"color": COLORS["green"], "fontSize": "22px",
                                                      "fontWeight": "800", "fontFamily": FONT_MONO}),
            html.Div("From your actual portfolio holdings",
                     style={"color": COLORS["text3"], "fontSize": "11px", "marginTop": "4px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("MONTHLY INCOME", style={"color": COLORS["text3"], "fontSize": "10px",
                                              "fontWeight": "600"}),
            html.Div(f"${total_income/12:,.2f}", style={"color": COLORS["green"], "fontSize": "22px",
                                                         "fontWeight": "800", "fontFamily": FONT_MONO}),
            html.Div("Estimated monthly dividend",
                     style={"color": COLORS["text3"], "fontSize": "11px", "marginTop": "4px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("AVG PORTFOLIO YIELD", style={"color": COLORS["text3"], "fontSize": "10px",
                                                   "fontWeight": "600"}),
            html.Div(f"{avg_yield:.2f}%", style={"color": COLORS["blue"], "fontSize": "22px",
                                                   "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("DIVIDEND PAYERS", style={"color": COLORS["text3"], "fontSize": "10px",
                                               "fontWeight": "600"}),
            html.Div(f"{len(dividend_data)}", style={"color": COLORS["text"], "fontSize": "22px",
                                                      "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
    ], style={"display": "flex", "gap": "12px", "marginBottom": "20px"})

    cards = []
    for d in sorted(dividend_data, key=lambda x: x["yield"], reverse=True):
        sym = d["symbol"]
        yld = d["yield"]
        rate = d["rate"]
        shares = d["shares"]
        annual_income = d["annual_income"]
        recent = d["recent_divs"]
        in_pf = d["in_portfolio"]

        chart = html.Div()
        if recent is not None and len(recent) > 1:
            dates = [str(dt.date()) for dt in recent.index]
            vals = list(recent.values)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=dates, y=vals, marker_color=COLORS["blue"],
                                 text=[f"${v:.3f}" for v in vals],
                                 textposition="outside",
                                 textfont=dict(color=COLORS["text2"], size=10)))
            fig.update_layout(paper_bgcolor=COLORS["panel2"], plot_bgcolor=COLORS["panel2"],
                              font=dict(color=COLORS["text2"]),
                              margin=dict(l=0, r=0, t=10, b=0), height=120,
                              xaxis=dict(showgrid=False),
                              yaxis=dict(showgrid=False, showticklabels=False),
                              showlegend=False)
            chart = dcc.Graph(figure=fig, config={"displayModeBar": False})

        ex_str = "N/A"
        days_until = None
        if d["ex_date"]:
            try:
                ex_dt = datetime.fromtimestamp(d["ex_date"])
                ex_str = ex_dt.strftime("%Y-%m-%d")
                days_until = (ex_dt - datetime.now()).days
            except Exception:
                pass

        ex_color = COLORS["green"] if days_until and days_until <= 30 else COLORS["text2"]

        cards.append(html.Div([
            html.Div([
                html.Div([
                    html.Span(sym, style={"color": COLORS["text"], "fontWeight": "800",
                                          "fontSize": "18px", "fontFamily": FONT_MONO,
                                          "marginRight": "12px"}),
                    html.Span(f"{yld:.2f}% yield",
                              style={"color": COLORS["green"], "fontWeight": "700",
                                     "fontSize": "13px", "background": "#166534",
                                     "padding": "3px 10px", "borderRadius": "6px",
                                     "marginRight": "8px"}),
                    html.Span("IN PORTFOLIO" if in_pf else "",
                              style={"color": COLORS["blue"], "fontSize": "11px",
                                     "fontWeight": "600"}) if in_pf else html.Span(),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div(f"${rate:.3f}/share annually" if rate else "",
                             style={"color": COLORS["text2"], "fontSize": "12px", "textAlign": "right"}),
                    html.Div(f"Ex-div: {ex_str}",
                             style={"color": ex_color, "fontSize": "12px", "textAlign": "right"}),
                    html.Div(f"In {days_until} days" if days_until and days_until > 0 else
                             "⚡ Ex-div passed!" if days_until is not None and days_until <= 0 else "",
                             style={"color": ex_color, "fontSize": "11px", "fontWeight": "700",
                                    "textAlign": "right"}),
                ]),
            ], style={"display": "flex", "alignItems": "flex-start", "marginBottom": "12px"}),

            # Your actual income if in portfolio
            html.Div([
                html.Div([
                    html.Div("YOUR SHARES", style={"color": COLORS["text3"], "fontSize": "10px",
                                                   "fontWeight": "600"}),
                    html.Div(f"{shares:g}", style={"color": COLORS["text"], "fontSize": "16px",
                                                    "fontWeight": "700", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("ANNUAL INCOME", style={"color": COLORS["text3"], "fontSize": "10px",
                                                     "fontWeight": "600"}),
                    html.Div(f"${annual_income:.2f}", style={"color": COLORS["green"],
                                                              "fontSize": "16px", "fontWeight": "700",
                                                              "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("MONTHLY INCOME", style={"color": COLORS["text3"], "fontSize": "10px",
                                                      "fontWeight": "600"}),
                    html.Div(f"${annual_income/12:.2f}", style={"color": COLORS["green"],
                                                                 "fontSize": "16px", "fontWeight": "700",
                                                                 "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "12px", "background": COLORS["panel2"],
                      "borderRadius": "8px", "padding": "12px 16px", "marginBottom": "12px"})
            if in_pf else html.Div(),

            html.Div("RECENT DIVIDEND HISTORY",
                     style={"color": COLORS["text3"], "fontSize": "10px",
                            "fontWeight": "600", "letterSpacing": "0.5px", "marginBottom": "6px"}),
            chart,

            # Remove button
            html.Div(
                html.Span(f"✕ Remove {sym}", id={"type": "div-remove", "index": sym},
                          n_clicks=0,
                          style={"color": COLORS["text3"], "cursor": "pointer",
                                 "fontSize": "11px", "marginTop": "8px"}),
            ) if not in_pf else html.Div(),

        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderLeft": f"3px solid {COLORS['green']}",
                  "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "12px"}))

    return html.Div([
        add_form,
        html.Div("Dividend income calculated from your actual portfolio share counts. Non-portfolio tickers show yield only.",
                 style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"}),
        summary,
        html.Div(cards, id="div-cards"),
    ])



# ---------- Options Flow ----------
def get_unusual_options(symbols):
    """Find unusual options activity - high volume relative to open interest."""
    unusual = []
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            if not t.options:
                continue
            # Check next 3 expiries
            for expiry in t.options[:3]:
                try:
                    chain = t.option_chain(expiry)
                    for opt_type, df in [("CALL", chain.calls), ("PUT", chain.puts)]:
                        if df.empty:
                            continue
                        df = df.copy()
                        df["vol_oi_ratio"] = df["volume"] / (df["openInterest"] + 1)
                        # Flag unusual: volume > 500 AND vol/OI ratio > 2
                        unusual_df = df[
                            (df["volume"] > 100) &
                            (df["vol_oi_ratio"] > 1.5) &
                            (df["volume"].notna())
                        ].copy()
                        for _, row in unusual_df.iterrows():
                            unusual.append({
                                "symbol": sym,
                                "type": opt_type,
                                "strike": row["strike"],
                                "expiry": expiry,
                                "volume": int(row["volume"]),
                                "open_interest": int(row["openInterest"]),
                                "vol_oi_ratio": float(row["vol_oi_ratio"]),
                                "iv": float(row["impliedVolatility"]) * 100,
                                "last_price": float(row.get("lastPrice", 0)),
                            })
                except Exception:
                    continue
        except Exception:
            continue
    # Sort by volume descending
    unusual.sort(key=lambda x: x["volume"], reverse=True)
    return unusual[:50]


def options_flow_tab():
    from datetime import datetime
    import zoneinfo
    ny = datetime.now(zoneinfo.ZoneInfo('America/New_York'))
    weekday = ny.weekday()
    hour = ny.hour
    minute = ny.minute
    is_market_hours = (weekday < 5) and (hour > 9 or (hour == 9 and minute >= 30)) and (hour < 16)

    if not is_market_hours:
        next_open = "Monday" if weekday >= 4 else "Tomorrow"
        if weekday < 4 and hour >= 16:
            next_open = "Tomorrow at 9:30 AM ET"
        elif weekday == 4 and hour >= 16:
            next_open = "Monday at 9:30 AM ET"
        elif weekday >= 5:
            next_open = f"Monday at 9:30 AM ET"
        else:
            next_open = "Today at 9:30 AM ET"
        return html.Div([
            html.Div([
                html.Div("🔴", style={"fontSize": "48px", "textAlign": "center",
                                       "marginBottom": "16px"}),
                html.Div("Options Market Closed", style={"color": COLORS["text"],
                         "fontSize": "24px", "fontWeight": "800", "textAlign": "center",
                         "marginBottom": "8px"}),
                html.Div(f"Current time: {ny.strftime('%I:%M %p ET')}",
                         style={"color": COLORS["text2"], "textAlign": "center",
                                "marginBottom": "4px"}),
                html.Div(f"Next open: {next_open}",
                         style={"color": COLORS["green"], "textAlign": "center",
                                "fontWeight": "600", "marginBottom": "24px"}),
                html.Div([
                    html.Div("OPTIONS MARKET HOURS", style={"color": COLORS["text3"],
                             "fontSize": "11px", "fontWeight": "600",
                             "letterSpacing": "0.5px", "marginBottom": "12px",
                             "textAlign": "center"}),
                    html.Div([
                        html.Div([
                            html.Span("Monday — Friday", style={"color": COLORS["text"],
                                                                   "fontWeight": "600"}),
                            html.Span("9:30 AM — 4:00 PM ET",
                                      style={"color": COLORS["green"], "float": "right",
                                             "fontFamily": FONT_MONO}),
                        ], style={"padding": "10px 0",
                                  "borderBottom": f"1px solid {COLORS['border']}"}),
                        html.Div([
                            html.Span("Saturday — Sunday", style={"color": COLORS["text2"]}),
                            html.Span("Closed", style={"color": COLORS["red"],
                                                         "float": "right"}),
                        ], style={"padding": "10px 0"}),
                    ]),
                    html.Div("Options flow data shows unusual activity — high volume vs open interest — "                             "which signals institutional positioning before major moves.",
                             style={"color": COLORS["text3"], "fontSize": "12px",
                                    "marginTop": "16px", "lineHeight": "1.6",
                                    "textAlign": "center"}),
                ], style={"background": COLORS["panel"],
                          "border": f"1px solid {COLORS['border']}",
                          "borderRadius": "10px", "padding": "20px",
                          "maxWidth": "500px", "margin": "0 auto"}),
            ], style={"padding": "60px 20px"}),
        ])

    wl_symbols = []
    import json as _json
    try:
        wl_file = os.path.expanduser("~/tradingbot/config/watchlist.json")
        wl_symbols = _json.load(open(wl_file)) if os.path.exists(wl_file) else []
    except Exception:
        pass

    # Default to major stocks if watchlist is all ETFs
    default_stocks = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "SPY", "QQQ"]
    symbols = wl_symbols + [s for s in default_stocks if s not in wl_symbols]
    symbols = symbols[:12]  # limit to avoid slow loads

    unusual = get_unusual_options(symbols)

    if not unusual:
        return html.Div([
            html.Div("No unusual options activity detected for your tickers right now.",
                     style={"color": COLORS["text2"], "marginBottom": "8px"}),
            html.Div("Unusual activity = volume > 500 contracts AND volume/open interest ratio > 2x",
                     style={"color": COLORS["text3"], "fontSize": "12px"}),
        ])

    rows = []
    for u in unusual:
        is_call = u["type"] == "CALL"
        type_color = COLORS["green"] if is_call else COLORS["red"]
        type_bg = "#166534" if is_call else "#7f1d1d"

        # Sentiment signal
        if is_call and u["vol_oi_ratio"] > 5:
            signal = "🔥 Very Bullish"
            signal_color = COLORS["green"]
        elif is_call:
            signal = "📈 Bullish"
            signal_color = "#86efac"
        elif not is_call and u["vol_oi_ratio"] > 5:
            signal = "🔥 Very Bearish"
            signal_color = COLORS["red"]
        else:
            signal = "📉 Bearish"
            signal_color = "#fca5a5"

        rows.append(html.Div([
            html.Div([
                html.Span(u["symbol"], style={"color": COLORS["text"], "fontWeight": "800",
                                              "fontSize": "16px", "fontFamily": FONT_MONO,
                                              "marginRight": "10px"}),
                html.Span(u["type"], style={"color": type_color, "fontWeight": "700",
                                            "fontSize": "12px", "background": type_bg,
                                            "padding": "2px 8px", "borderRadius": "4px",
                                            "marginRight": "10px"}),
                html.Span(signal, style={"color": signal_color, "fontSize": "12px",
                                         "fontWeight": "600"}),
            ], style={"flex": "1"}),
            html.Div([
                html.Span(f"Strike: ${u['strike']:.0f}",
                          style={"color": COLORS["text2"], "fontSize": "12px",
                                 "fontFamily": FONT_MONO, "marginRight": "16px"}),
                html.Span(f"Exp: {u['expiry']}",
                          style={"color": COLORS["text2"], "fontSize": "12px",
                                 "marginRight": "16px"}),
                html.Span(f"Vol: {u['volume']:,}",
                          style={"color": COLORS["text"], "fontSize": "12px",
                                 "fontWeight": "700", "fontFamily": FONT_MONO,
                                 "marginRight": "16px"}),
                html.Span(f"OI: {u['open_interest']:,}",
                          style={"color": COLORS["text2"], "fontSize": "12px",
                                 "fontFamily": FONT_MONO, "marginRight": "16px"}),
                html.Span(f"Vol/OI: {u['vol_oi_ratio']:.1f}x",
                          style={"color": type_color, "fontSize": "12px",
                                 "fontWeight": "700", "fontFamily": FONT_MONO,
                                 "marginRight": "16px"}),
                html.Span(f"IV: {u['iv']:.0f}%",
                          style={"color": COLORS["amber"], "fontSize": "12px",
                                 "fontFamily": FONT_MONO}),
            ]),
        ], style={
            "background": COLORS["panel"],
            "border": f"1px solid {COLORS['border']}",
            "borderLeft": f"3px solid {type_color}",
            "borderRadius": "8px", "padding": "12px 16px", "marginBottom": "6px",
            "display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "8px",
        }))

    # Summary
    calls = sum(1 for u in unusual if u["type"] == "CALL")
    puts = len(unusual) - calls
    put_call = puts / calls if calls > 0 else 0
    pcr_color = COLORS["red"] if put_call > 1 else COLORS["green"]
    pcr_sentiment = "Bearish" if put_call > 1.2 else "Bullish" if put_call < 0.8 else "Neutral"

    summary = html.Div([
        html.Div([
            html.Div("UNUSUAL CALLS", style={"color": COLORS["text3"], "fontSize": "10px",
                                             "fontWeight": "600"}),
            html.Div(str(calls), style={"color": COLORS["green"], "fontSize": "22px",
                                        "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("UNUSUAL PUTS", style={"color": COLORS["text3"], "fontSize": "10px",
                                            "fontWeight": "600"}),
            html.Div(str(puts), style={"color": COLORS["red"], "fontSize": "22px",
                                       "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("PUT/CALL RATIO", style={"color": COLORS["text3"], "fontSize": "10px",
                                              "fontWeight": "600"}),
            html.Div(f"{put_call:.2f}", style={"color": pcr_color, "fontSize": "22px",
                                                "fontWeight": "800", "fontFamily": FONT_MONO}),
            html.Div(pcr_sentiment, style={"color": pcr_color, "fontSize": "11px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("TOTAL UNUSUAL", style={"color": COLORS["text3"], "fontSize": "10px",
                                             "fontWeight": "600"}),
            html.Div(str(len(unusual)), style={"color": COLORS["text"], "fontSize": "22px",
                                               "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
    ], style={"display": "flex", "gap": "12px", "marginBottom": "20px"})

    return html.Div([
        html.Div([
            html.Div("Unusual options activity = volume > 500 contracts AND volume/open interest > 2x. "
                     "High call volume = bullish bet. High put volume = bearish hedge or bet. "
                     "Vol/OI > 5x = very strong signal.",
                     style={"color": COLORS["text3"], "fontSize": "12px"}),
        ], style={"marginBottom": "16px"}),
        summary,
        html.Div(rows),
    ])


# ---------- Short Interest ----------
def short_interest_tab():
    import json as _json
    from datetime import datetime

    wl_file = os.path.expanduser("~/tradingbot/config/watchlist.json")
    try:
        wl = _json.load(open(wl_file)) if os.path.exists(wl_file) else []
    except Exception:
        wl = []

    default_stocks = [
        "AAPL","MSFT","NVDA","TSLA","GOOGL","AMZN","META","JPM","V","JNJ",
        "WMT","PG","MA","HD","BAC","XOM","PFE","ABBV","KO","PEP","AVGO",
        "COST","MRK","CVX","TMO","ABT","CRM","ACN","MCD","NFLX","ADBE",
        "NKE","DHR","TXN","PM","NEE","ORCL","AMD","QCOM","LIN","UPS",
        "RTX","HON","AMGN","IBM","GS","CAT","SBUX","GE","F","GM",
        "RIVN","LCID","PLTR","SOFI","AMC","GME","BBBY","COIN","HOOD"
    ]
    symbols = list(dict.fromkeys(wl + default_stocks))[:50]

    data = []
    if _FAST_FETCH:
        all_info = fetch_many_info(symbols, max_workers=12)
    else:
        all_info = {sym: yf.Ticker(sym).info for sym in symbols}

    for sym in symbols:
        try:
            info = all_info.get(sym, {})
            short_pct = info.get("shortPercentOfFloat", 0) or 0
            short_ratio = info.get("shortRatio", 0) or 0
            shares_short = info.get("sharesShort", 0) or 0
            shares_prior = info.get("sharesShortPriorMonth", 0) or 0
            date_ts = info.get("dateShortInterest", 0)
            date_str = datetime.fromtimestamp(date_ts).strftime("%Y-%m-%d") if date_ts else "N/A"
            change = shares_short - shares_prior
            change_pct = (change / shares_prior * 100) if shares_prior else 0

            if shares_short > 0:
                data.append({
                    "symbol": sym,
                    "short_pct": short_pct * 100 if short_pct < 1 else short_pct,
                    "short_ratio": short_ratio,
                    "shares_short": shares_short,
                    "shares_prior": shares_prior,
                    "change": change,
                    "change_pct": change_pct,
                    "date": date_str,
                })
        except Exception:
            continue

    if not data:
        return html.Div("No short interest data available.", style={"color": COLORS["text2"]})

    # Sort by short % descending
    data.sort(key=lambda x: x["short_pct"], reverse=True)

    # Summary
    most_shorted = data[0]
    least_shorted = data[-1]
    avg_short = sum(d["short_pct"] for d in data) / len(data)
    increasing = sum(1 for d in data if d["change"] > 0)

    summary = html.Div([
        html.Div([
            html.Div("MOST SHORTED", style={"color": COLORS["text3"], "fontSize": "10px",
                                            "fontWeight": "600"}),
            html.Div(most_shorted["symbol"], style={"color": COLORS["red"], "fontSize": "22px",
                                                     "fontWeight": "800", "fontFamily": FONT_MONO}),
            html.Div(f"{most_shorted['short_pct']:.2f}% of float",
                     style={"color": COLORS["red"], "fontSize": "12px", "fontWeight": "600"}),
            html.Div(f"{most_shorted['short_ratio']:.1f} days to cover",
                     style={"color": COLORS["text3"], "fontSize": "11px"}),
        ], style={"background": COLORS["panel"], "border": f"2px solid {COLORS['red']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("LEAST SHORTED", style={"color": COLORS["text3"], "fontSize": "10px",
                                             "fontWeight": "600"}),
            html.Div(least_shorted["symbol"], style={"color": COLORS["green"], "fontSize": "22px",
                                                      "fontWeight": "800", "fontFamily": FONT_MONO}),
            html.Div(f"{least_shorted['short_pct']:.2f}% of float",
                     style={"color": COLORS["green"], "fontSize": "12px", "fontWeight": "600"}),
            html.Div(f"{least_shorted['short_ratio']:.1f} days to cover",
                     style={"color": COLORS["text3"], "fontSize": "11px"}),
        ], style={"background": COLORS["panel"], "border": f"2px solid {COLORS['green']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("AVG SHORT INTEREST", style={"color": COLORS["text3"], "fontSize": "10px",
                                                  "fontWeight": "600"}),
            html.Div(f"{avg_short:.2f}%", style={"color": COLORS["amber"], "fontSize": "22px",
                                                   "fontWeight": "800", "fontFamily": FONT_MONO}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
        html.Div([
            html.Div("SHORT INCREASING", style={"color": COLORS["text3"], "fontSize": "10px",
                                                "fontWeight": "600"}),
            html.Div(f"{increasing}/{len(data)}",
                     style={"color": COLORS["red"] if increasing > len(data)/2 else COLORS["green"],
                            "fontSize": "22px", "fontWeight": "800", "fontFamily": FONT_MONO}),
            html.Div("vs prior month", style={"color": COLORS["text3"], "fontSize": "11px"}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "14px 18px", "flex": "1"}),
    ], style={"display": "flex", "gap": "12px", "marginBottom": "20px"})

    rows = []
    for d in data:
        short_pct = d["short_pct"]
        change_pct = d["change_pct"]
        change_color = COLORS["red"] if change_pct > 0 else COLORS["green"]
        change_arrow = "▲" if change_pct > 0 else "▼"

        # Risk level
        if short_pct > 20:
            risk = "🔥 Extreme"
            risk_color = "#dc2626"
        elif short_pct > 10:
            risk = "⚠️ High"
            risk_color = COLORS["red"]
        elif short_pct > 5:
            risk = "⚡ Moderate"
            risk_color = COLORS["amber"]
        else:
            risk = "✅ Low"
            risk_color = COLORS["green"]

        # Short squeeze potential
        squeeze = "🚀 High Squeeze Risk" if short_pct > 15 and d["short_ratio"] > 5 else ""

        # Bar showing short % of float
        bar_width = min(short_pct * 3, 100)  # scale for display

        rows.append(html.Div([
            html.Div([
                html.Div([
                    html.Span(d["symbol"], style={"color": COLORS["text"], "fontWeight": "800",
                                                   "fontSize": "18px", "fontFamily": FONT_MONO,
                                                   "marginRight": "12px"}),
                    html.Span(risk, style={"color": risk_color, "fontSize": "12px",
                                           "fontWeight": "600", "marginRight": "12px"}),
                    html.Span(squeeze, style={"color": "#f59e0b", "fontSize": "12px",
                                              "fontWeight": "700"}) if squeeze else html.Span(),
                ], style={"flex": "1"}),
                html.Div(f"As of {d['date']}",
                         style={"color": COLORS["text3"], "fontSize": "11px"}),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "12px"}),

            # Short % bar
            html.Div([
                html.Div(f"Short % of Float: {short_pct:.2f}%",
                         style={"color": COLORS["text2"], "fontSize": "12px",
                                "marginBottom": "4px"}),
                html.Div(
                    html.Div(style={"width": f"{bar_width}%",
                                    "background": risk_color,
                                    "height": "8px", "borderRadius": "4px"}),
                    style={"background": COLORS["border"], "borderRadius": "4px",
                           "height": "8px", "marginBottom": "12px"}),
            ]),

            # Stats row
            html.Div([
                html.Div([
                    html.Div("SHARES SHORT", style={"color": COLORS["text3"], "fontSize": "10px",
                                                    "fontWeight": "600"}),
                    html.Div(f"{d['shares_short']:,}", style={"color": COLORS["text"],
                                                               "fontSize": "14px", "fontWeight": "700",
                                                               "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("PRIOR MONTH", style={"color": COLORS["text3"], "fontSize": "10px",
                                                   "fontWeight": "600"}),
                    html.Div(f"{d['shares_prior']:,}", style={"color": COLORS["text2"],
                                                               "fontSize": "14px",
                                                               "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("CHANGE", style={"color": COLORS["text3"], "fontSize": "10px",
                                              "fontWeight": "600"}),
                    html.Div(f"{change_arrow} {abs(d['change']):,} ({change_pct:+.1f}%)",
                             style={"color": change_color, "fontSize": "14px",
                                    "fontWeight": "700", "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Div("DAYS TO COVER", style={"color": COLORS["text3"], "fontSize": "10px",
                                                     "fontWeight": "600"}),
                    html.Div(f"{d['short_ratio']:.1f} days",
                             style={"color": COLORS["amber"] if d["short_ratio"] > 3 else COLORS["text2"],
                                    "fontSize": "14px", "fontWeight": "700",
                                    "fontFamily": FONT_MONO}),
                ], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "12px", "background": COLORS["panel2"],
                      "borderRadius": "8px", "padding": "12px 16px"}),
        ], style={"background": COLORS["panel"],
                  "border": f"1px solid {COLORS['border']}",
                  "borderLeft": f"3px solid {risk_color}",
                  "borderRadius": "10px", "padding": "16px 20px",
                  "marginBottom": "12px"}))

    return html.Div([
        html.Div("Short interest shows how many shares are being borrowed and sold short. "
                 "High short % = bearish sentiment. High Days to Cover + High Short % = short squeeze risk.",
                 style={"color": COLORS["text3"], "fontSize": "12px", "marginBottom": "16px"}),
        summary,
        html.Div(rows),
    ])


def paper_trading_tab():
    """
    Real, live paper trading status -- pulls directly from the
    live_regime_state and paper_performance_history tables built
    tonight, showing the actual, current state of the running
    IBKR paper trading system, not mock data.
    """
    import sys
    import os
    sys.path.insert(0, os.path.expanduser("~/tradingbot/engine"))
    from db_setup import get_connection

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT date, regime, pct_below, avg_correlation
        FROM live_regime_state ORDER BY date DESC LIMIT 1
    """)
    latest_regime = c.fetchone()

    c.execute("""
        SELECT date, regime FROM live_regime_state
        ORDER BY date DESC LIMIT 14
    """)
    regime_history = c.fetchall()

    c.execute("""
        SELECT date, account_value FROM paper_performance_history
        ORDER BY date ASC
    """)
    perf_history = c.fetchall()

    conn.close()

    regime_card = html.Div([
        html.H4("Current Regime", style={"color": "#4b8bf5"}),
        html.H2(latest_regime["regime"] if latest_regime else "No data",
               style={"color": "#00ff88" if latest_regime and latest_regime["regime"] == "CALM"
                     else "#ff4444" if latest_regime and latest_regime["regime"] == "SYSTEMIC_CRISIS"
                     else "#ffaa00"}),
        html.P(f"As of: {latest_regime['date'] if latest_regime else 'N/A'}"),
        html.P(f"Breadth: {latest_regime['pct_below']:.1%}" if latest_regime else ""),
        html.P(f"Correlation: {latest_regime['avg_correlation']:.3f}" if latest_regime else ""),
    ], style={"padding": "20px", "border": "1px solid #333", "borderRadius": "8px",
             "marginBottom": "20px"})

    regime_history_rows = [
        html.Tr([html.Td(r["date"]), html.Td(r["regime"])])
        for r in regime_history
    ]
    history_table = html.Div([
        html.H4("Recent Regime History"),
        html.Table([
            html.Thead(html.Tr([html.Th("Date"), html.Th("Regime")])),
            html.Tbody(regime_history_rows),
        ], style={"width": "100%"}),
    ], style={"padding": "20px", "border": "1px solid #333", "borderRadius": "8px",
             "marginBottom": "20px"})

    if perf_history:
        start_val = perf_history[0]["account_value"]
        latest_val = perf_history[-1]["account_value"]
        change = (latest_val - start_val) / start_val
        perf_chart = dcc.Graph(figure={
            "data": [{
                "x": [r["date"] for r in perf_history],
                "y": [r["account_value"] for r in perf_history],
                "type": "line", "name": "Paper Account Value",
                "line": {"color": COLORS["blue"]},
            }],
            "layout": {
                "title": f"Paper Account Value (change: {change:+.2%})",
                "paper_bgcolor": COLORS["panel"],
                "plot_bgcolor": COLORS["panel"],
                "font": {"color": COLORS["text2"]},
            },
        })
    else:
        perf_chart = html.P("No performance history recorded yet.")

    # Real, intraday history from the frequent live poller --
    # separate from the once-daily paper_performance_history table
    conn2 = get_connection()
    c2 = conn2.cursor()
    c2.execute("""
        CREATE TABLE IF NOT EXISTS live_value_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            account_value REAL
        )
    """)
    c2.execute("""
        SELECT timestamp, account_value FROM live_value_snapshots
        ORDER BY id DESC LIMIT 200
    """)
    intraday_rows = list(reversed(c2.fetchall()))
    conn2.close()

    if intraday_rows:
        intraday_chart = dcc.Graph(figure={
            "data": [{
                "x": [r["timestamp"] for r in intraday_rows],
                "y": [r["account_value"] for r in intraday_rows],
                "type": "line", "name": "Live Value",
                "line": {"color": COLORS["blue"]},
            }],
            "layout": {
                "title": "Intraday Portfolio Value (live poller, ~2min intervals)",
                "paper_bgcolor": COLORS["panel"],
                "plot_bgcolor": COLORS["panel"],
                "font": {"color": COLORS["text2"]},
            },
        }, id="intraday-chart")
    else:
        intraday_chart = html.P("No intraday data yet -- poller just started.")

    # Real, live portfolio value pulled directly from IBKR right now
    live_value_card = html.Div([
        html.H4("Live Portfolio Value", style={"color": COLORS["blue"]}),
        html.Div(id="live-portfolio-value", style={"fontSize": "2.5em", "fontWeight": "bold"}),
        html.Div(id="live-portfolio-change", style={"fontSize": "1.2em"}),
        dcc.Interval(id="paper-value-interval", interval=30*1000, n_intervals=0),
    ], style={"padding": "20px", "border": "1px solid #333", "borderRadius": "8px",
             "marginBottom": "20px"})

    return html.Div([
        html.H2("📝 Live Paper Trading (IBKR)"),
        live_value_card,
        html.Div([intraday_chart], id="intraday-chart-container",
                 style={"padding": "20px", "border": "1px solid #333",
                       "borderRadius": "8px", "marginBottom": "20px"}),
        regime_card,
        history_table,
        html.Div([perf_chart], style={"padding": "20px", "border": "1px solid #333",
                                       "borderRadius": "8px"}),
    ])
