"""
Market Terminal — Dash version
Run: python ~/tradingbot/dashboard/dash_app.py
"""
import os
import sys
import json
from datetime import datetime
import zoneinfo

import dash
from dash import dcc, html, Input, Output, State, callback, ctx, ALL
import dash_bootstrap_components as dbc
import yfinance as yf
import plotly.graph_objects as go
from dotenv import load_dotenv

sys.path.append(os.path.expanduser("~/tradingbot/engine"))
sys.path.append(os.path.expanduser("~/tradingbot/dashboard"))
from data_sources import get_news
from ai_utils import generate_ai_text
import dash_pages
from dash_pages import (news_grid, article_detail, ticker_detail_page,
    snapshot_bar, sentiment_gauge, earnings_tab, insider_tab, sec_tab, get_insider_trades,
    category_content, browse_tab_content, portfolio_tab,
    load_portfolio, save_portfolio, breakdown_tab, correlation_tab,
    market_map_tab, market_treemap, portfolio_treemap, sector_treemap, etf_treemap,
    compare_tab, compare_results, economic_tab, backtest_tab,
    alerts_tab, load_alerts, save_alerts, check_alerts, crypto_tab,
    bot_control_tab, load_bot_config, save_bot_config,
    analyst_ratings_tab, dividend_tracker_tab, options_flow_tab)

# Import news fetching from the streamlit module's logic (rebuilt here without st.cache)
import requests as _req

_news_cache = {"feed": [], "source": None, "fetched_at": None}

def fetch_news_dash(limit=50):
    """Same 5-source fallover as news_view.py but with simple time-based cache."""
    import time
    now = time.time()
    if _news_cache["fetched_at"] and now - _news_cache["fetched_at"] < 1800 and _news_cache["feed"]:
        return _news_cache["feed"], _news_cache["source"]

    av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    feed, source = [], None

    # Alpha Vantage
    try:
        resp = _req.get("https://www.alphavantage.co/query", params={
            "function": "NEWS_SENTIMENT", "apikey": av_key,
            "limit": limit, "sort": "LATEST"}, timeout=15)
        data = resp.json()
        if "feed" in data and data["feed"]:
            feed, source = data["feed"], "Alpha Vantage"
    except Exception:
        pass

    # Finnhub fallback
    if not feed:
        try:
            fh_key = os.getenv("FINNHUB_API_KEY")
            resp = _req.get("https://finnhub.io/api/v1/news",
                            params={"category": "general", "token": fh_key}, timeout=15)
            raw = resp.json()
            if isinstance(raw, list) and raw:
                for a in raw[:limit]:
                    feed.append({
                        "title": a.get("headline", ""),
                        "summary": a.get("summary", ""),
                        "url": a.get("url", "#"),
                        "banner_image": a.get("image", ""),
                        "source": a.get("source", ""),
                        "time_published": datetime.utcfromtimestamp(
                            int(a.get("datetime", 0))).strftime("%Y%m%dT%H%M%S") if a.get("datetime") else "",
                        "overall_sentiment_label": "Neutral",
                        "overall_sentiment_score": 0,
                    })
                source = "Finnhub"
                # Score sentiment with AI since Finnhub has no sentiment
                try:
                    titles = [a["title"] for a in feed]
                    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
                    s_prompt = (
                        "You are a financial sentiment analyst. For each headline below, "
                        "respond with ONLY the number and one of these exact labels: "
                        "Bullish, Somewhat-Bullish, Neutral, Somewhat-Bearish, Bearish.\n"
                        "One per line, no explanation.\n\n" + numbered
                    )
                    result = generate_ai_text(s_prompt)
                    score_map = {"Bullish": 0.5, "Somewhat-Bullish": 0.25,
                                 "Neutral": 0.0, "Somewhat-Bearish": -0.25, "Bearish": -0.5}
                    for i, line in enumerate(result.strip().split("\n")):
                        if i >= len(feed):
                            break
                        parts = line.strip().split(" ", 1)
                        lab = parts[-1].strip() if len(parts) > 1 else "Neutral"
                        if lab in score_map:
                            feed[i]["overall_sentiment_label"] = lab
                            feed[i]["overall_sentiment_score"] = score_map[lab]
                except Exception:
                    pass
        except Exception:
            pass

    if feed:
        _news_cache["feed"] = feed
        _news_cache["source"] = source
        _news_cache["fetched_at"] = now
    return feed, source

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))

# ---------- Theme ----------
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

# ---------- Constants ----------
TAPE_STOCKS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
TAPE_ETFS = ["SPY", "QQQ", "VOO", "VTI", "DIA"]
TAPE_INDICES = {"^GSPC": "S&P 500", "^DJI": "DOW", "^IXIC": "NASDAQ", "^FTSE": "FTSE 100", "^N225": "NIKKEI"}

CATEGORY_TICKERS = {
    "Stocks": "AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA",
    "ETFs": "SPY,QQQ,VOO,VTI,DIA",
    "World": "^GSPC,^DJI,^IXIC,^FTSE,^N225"
}

WATCHLIST_FILE = os.path.expanduser("~/tradingbot/config/watchlist.json")

def load_watchlist_symbols():
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ", "BND", "VTI"]

def save_watchlist_symbols(symbols):
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(symbols, f)
    except Exception:
        pass

# ---------- Data helpers ----------
def get_tape_data():
    all_symbols = TAPE_STOCKS + TAPE_ETFS + list(TAPE_INDICES.keys())
    results = []
    try:
        data = yf.download(all_symbols, period="2d", progress=False, group_by="ticker")
        for sym in all_symbols:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    pct = ((curr - prev) / prev) * 100
                    label = TAPE_INDICES.get(sym, sym)
                    results.append((label, curr, pct))
            except Exception:
                continue
    except Exception:
        pass
    return results

def get_market_status():
    ny = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.now(ny)
    weekday = now.weekday()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if weekday >= 5:
        return "closed", "Markets closed (Weekend)"
    if now < market_open:
        delta = market_open - now
        mins = int(delta.total_seconds() // 60)
        return "pre", f"Pre-market — opens in {mins//60}h {mins%60}m"
    if now > market_close:
        delta = now - market_close
        mins = int(delta.total_seconds() // 60)
        return "closed", f"Markets closed — {mins//60}h {mins%60}m ago"
    delta = market_close - now
    mins = int(delta.total_seconds() // 60)
    return "open", f"Markets open — closes in {mins//60}h {mins%60}m"

def get_watchlist_data():
    symbols = load_watchlist_symbols()
    results = []
    try:
        data = yf.download(symbols, period="2d", progress=False, group_by="ticker")
        for sym in symbols:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    pct = ((curr - prev) / prev) * 100
                    results.append((sym, curr, pct))
            except Exception:
                continue
    except Exception:
        pass
    return results

# ---------- Components ----------
def ticker_tape():
    data = get_tape_data()
    items = []
    for label, price, pct in data * 2:  # duplicate for smooth scroll
        color = COLORS["green"] if pct >= 0 else COLORS["red"]
        arrow = "▲" if pct >= 0 else "▼"
        items.append(html.Span([
            html.Span(label, style={"color": COLORS["text2"], "fontWeight": "600", "marginRight": "6px"}),
            html.Span(f"{price:.2f} ", style={"color": COLORS["text"]}),
            html.Span(f"{arrow} {pct:+.2f}%", style={"color": color}),
        ], style={"marginRight": "36px", "fontFamily": FONT_MONO, "fontSize": "13px", "display": "inline-block"}))
    return html.Div(
        html.Div(items, className="tape-track"),
        className="tape-wrap"
    )

def get_watchlist_rows():
    data = get_watchlist_data()
    rows = []
    for sym, price, pct in data:
        color = COLORS["green"] if pct >= 0 else COLORS["red"]
        arrow = "▲" if pct >= 0 else "▼"
        rows.append(
            html.Div([
                html.Div(
                    sym,
                    id={"type": "wl-item", "index": sym},
                    n_clicks=0,
                    style={"color": COLORS["text"], "fontWeight": "700",
                           "fontSize": "13px", "fontFamily": FONT_MONO,
                           "cursor": "pointer", "flex": "1"}
                ),
                html.Span(f"${price:.2f}", style={"color": COLORS["text2"],
                                                   "fontSize": "12px",
                                                   "fontFamily": FONT_MONO,
                                                   "marginRight": "12px"}),
                html.Span(f"{arrow}{pct:+.2f}%", style={"color": color,
                                                          "fontSize": "12px",
                                                          "fontWeight": "700",
                                                          "marginRight": "12px"}),
                html.Div("✕", id={"type": "wl-remove", "index": sym},
                         n_clicks=0,
                         style={"color": COLORS["text3"], "cursor": "pointer",
                                "marginLeft": "10px", "fontSize": "14px",
                                "fontWeight": "700", "padding": "2px 8px"}),
            ], className="watchlist-row", style={
                "background": COLORS["panel"],
                "border": f"1px solid {COLORS['border2']}",
                "borderRadius": "8px",
                "padding": "10px 14px",
                "marginBottom": "6px",
                "display": "flex",
                "alignItems": "center",
            })
        )
    return rows

def watchlist_panel():
    return html.Div(get_watchlist_rows(), id="watchlist-container")

def _bot_status_panel():
    try:
        status_file = os.path.expanduser("~/tradingbot/engine/bot_status.json")
        if os.path.exists(status_file):
            with open(status_file) as f:
                bot = json.load(f)
            return html.Div([
                html.Div("● RUNNING", style={"color": COLORS["green"], "fontSize": "12px", "fontWeight": "700"}),
                html.Div(f"Last rebalance: {bot.get('last_rebalance', 'N/A')}",
                         style={"color": COLORS["text2"], "fontSize": "11px", "marginTop": "4px"}),
                html.Div(f"Next rebalance: {bot.get('next_rebalance', 'N/A')}",
                         style={"color": COLORS["text2"], "fontSize": "11px"}),
            ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                      "borderRadius": "8px", "padding": "10px 14px"})
    except Exception:
        pass
    return html.Div([
        html.Div("● NOT RUNNING", style={"color": COLORS["red"], "fontSize": "12px", "fontWeight": "700"}),
        html.Div("Engine offline", style={"color": COLORS["text3"], "fontSize": "11px", "marginTop": "4px"}),
    ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
              "borderRadius": "8px", "padding": "10px 14px"})


def sidebar():
    status, status_msg = get_market_status()
    status_color = COLORS["green"] if status == "open" else "#f59e0b" if status == "pre" else COLORS["red"]
    return html.Div([
        html.H5("Market Status", style={"color": COLORS["text"], "marginTop": "20px"}),
        html.Div([
            html.Span(f"● {status_msg}", style={"color": status_color, "fontWeight": "700", "fontSize": "13px"}),
        ], style={
            "background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
            "borderLeft": f"3px solid {status_color}", "borderRadius": "8px",
            "padding": "10px 14px", "marginBottom": "16px",
        }),
        html.H5("Watchlist", style={"color": COLORS["text"]}),
        html.Datalist(id="ticker-datalist", children=[
            html.Option(value=s) for s in [
                "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","BRK-B","JPM","V",
                "JNJ","WMT","PG","MA","HD","BAC","XOM","PFE","ABBV","KO","PEP","AVGO",
                "COST","MRK","CVX","TMO","ABT","CRM","ACN","MCD","NFLX","ADBE","NKE",
                "DHR","TXN","PM","NEE","ORCL","AMD","QCOM","LIN","UPS","RTX","HON",
                "AMGN","IBM","GS","CAT","SBUX","GE",
                "SPY","QQQ","VTI","VOO","IWM","DIA","GLD","SLV","TLT","HYG",
                "VNQ","XLF","XLK","XLE","XLV","XLI","XLY","XLP","XLU","XLB",
                "BND","AGG","LQD","EMB","VCIT","VCSH","BSV","BNDX","MUB","VTEB",
            ]
        ]),
        dbc.Input(
            id="add-ticker-input",
            placeholder="Type or search any ticker...",
            list="ticker-datalist",
            style={"backgroundColor": "#11161f", "border": "1px solid #2d3748",
                   "color": "#e2e8f0", "marginBottom": "8px"},
        ),
        dbc.Button("Add", id="add-ticker-btn", color="primary", size="sm", className="mb-3 w-100"),
        watchlist_panel(),
        html.Hr(style={"borderColor": COLORS["border"]}),
        html.H5("Bot Status", style={"color": COLORS["text"]}),
        _bot_status_panel(),
    ], style={
        "width": "300px", "minWidth": "300px", "padding": "20px",
        "background": "#0d1219", "borderRight": f"1px solid {COLORS['border']}",
        "height": "100vh", "overflowY": "auto",
    })

# ---------- App ----------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY],
                suppress_callback_exceptions=True)
app.title = "Market Terminal"

app.layout = html.Div([
    dcc.Store(id="selected-ticker", data=None),
    dcc.Store(id="selected-article", data=None),
    dcc.Store(id="chart-period", data="1y"),
    dcc.Store(id="compare-list", data=[]),
    html.Div(id="alert-notifications", style={"position": "fixed", "top": "10px", "right": "10px", "zIndex": "9999", "maxWidth": "400px"}),
    dcc.Interval(id="refresh-interval", interval=60_000),
    html.Div([
        sidebar(),
        html.Div([
            ticker_tape(),
            html.Div([
                html.Span("Market ", style={"color": COLORS["text"], "fontSize": "22px", "fontWeight": "700"}),
                html.Span("Terminal", style={"color": COLORS["blue"], "fontSize": "22px", "fontWeight": "700"}),
            ], style={"padding": "10px 24px", "borderBottom": f"1px solid {COLORS['border']}"}),
            html.Div(id="main-content", style={"padding": "24px"}),
        ], style={"flex": "1", "overflowY": "auto", "height": "100vh"}),
    ], style={"display": "flex", "background": COLORS["bg"]}),
], style={"background": COLORS["bg"], "minHeight": "100vh"})

# ---------- Callbacks ----------
@callback(
    Output("main-content", "children"),
    Input("selected-ticker", "data"),
    Input("selected-article", "data"),
)
def render_main(selected_ticker, selected_article_idx):
    if selected_ticker:
        return ticker_detail_page(selected_ticker)
    if selected_article_idx is not None:
        feed, _ = fetch_news_dash()
        def _good_image(a):
            img = a.get("banner_image", "")
            if not img:
                return False
            bad = ["logo", "icon", "avatar", "placeholder", "default", "blank"]
            return not any(b in img.lower() for b in bad)
        with_img = [a for a in feed if _good_image(a)]
        if selected_article_idx < len(with_img):
            article = with_img[selected_article_idx]
            url = article.get("url", "")
            insight = _article_insights.get(url)
            if insight is None:
                label = article.get("overall_sentiment_label", "Neutral")
                prompt = (
                    f"You are a senior financial analyst. Analyze this news article and provide a deep professional breakdown.\n\n"
                    f"**KEY TAKEAWAY**\n2-3 sentences on what this article is actually saying.\n\n"
                    f"**MARKET IMPACT**\nHow does this affect markets, sectors, or specific companies?\n\n"
                    f"**RISK/OPPORTUNITY**\nWhat risk or opportunity does this signal for investors?\n\n"
                    f"**BOTTOM LINE**\n1-2 sentences summarizing the key insight.\n\n"
                    f"Article Title: {article.get('title', '')}\n"
                    f"Summary: {article.get('summary', '')}\n"
                    f"Source: {article.get('source', '')}\n"
                    f"Sentiment: {label}"
                )
                insight = generate_ai_text(prompt)
                _article_insights[url] = insight
            return article_detail(article, insight)
    # Default: tabs
    return html.Div([
        dbc.Tabs([
            dbc.Tab(label="📰 News", tab_id="tab-news"),
            dbc.Tab(label="Stocks", tab_id="tab-stocks"),
            dbc.Tab(label="ETFs", tab_id="tab-etfs"),
            dbc.Tab(label="World", tab_id="tab-world"),
            dbc.Tab(label="Browse", tab_id="tab-browse"),
            dbc.Tab(label="💼 Portfolio", tab_id="tab-portfolio"),
            dbc.Tab(label="🧭 Breakdown", tab_id="tab-breakdown"),
            dbc.Tab(label="🔗 Correlation", tab_id="tab-correlation"),
            dbc.Tab(label="🗺️ Map", tab_id="tab-map"),
            dbc.Tab(label="⚖️ Compare", tab_id="tab-compare"),
            dbc.Tab(label="📈 Economy", tab_id="tab-economy"),
            dbc.Tab(label="⏱️ Backtest", tab_id="tab-backtest"),
            dbc.Tab(label="🔔 Alerts", tab_id="tab-alerts"),
            dbc.Tab(label="₿ Crypto", tab_id="tab-crypto"),
            dbc.Tab(label="🤖 Bot", tab_id="tab-bot"),
            dbc.Tab(label="⭐ Ratings", tab_id="tab-ratings"),
            dbc.Tab(label="💰 Dividends", tab_id="tab-dividends"),
            dbc.Tab(label="🌊 Flow", tab_id="tab-options"),
        ], id="main-tabs", active_tab="tab-news"),
        dcc.Loading(html.Div(id="tab-content", style={"marginTop": "20px"}), type="circle", color="#4b8bf5"),
    ])


_article_insights = {}


@callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab"),
)
def render_tab(active_tab):
    if active_tab == "tab-news":
        feed, source = fetch_news_dash()
        if not feed:
            return html.Div("All news sources unavailable. Try again in a few minutes.",
                            style={"color": COLORS["text2"]})
        return html.Div([
            html.Div(f"Source: {source}", style={"color": COLORS["text3"],
                                                  "fontSize": "12px", "marginBottom": "12px"}),
            snapshot_bar(),
            sentiment_gauge(feed),
            dbc.Tabs([
                dbc.Tab(label="📰 Top News", tab_id="sub-news"),
                dbc.Tab(label="📅 Earnings", tab_id="sub-earnings"),
                dbc.Tab(label="📊 Insider Trading", tab_id="sub-insider"),
                dbc.Tab(label="📄 SEC Filings", tab_id="sub-sec"),
            ], id="news-subtabs", active_tab="sub-news"),
            html.Div(id="news-subtab-content", style={"marginTop": "20px"}),
        ])
    if active_tab in ("tab-stocks", "tab-etfs", "tab-world"):
        cat_map = {"tab-stocks": "Stocks", "tab-etfs": "ETFs", "tab-world": "World"}
        category = cat_map[active_tab]
        articles = _get_category_articles(category)
        summary = _get_category_summary(category, articles)
        active_filter = _category_filters.get(category, "All")
        return category_content(category, articles, active_filter, summary)
    if active_tab == "tab-portfolio":
        return portfolio_tab()
    if active_tab == "tab-breakdown":
        return breakdown_tab()
    if active_tab == "tab-correlation":
        return correlation_tab()
    if active_tab == "tab-map":
        return market_map_tab()
    if active_tab == "tab-compare":
        return compare_tab(_compare_list)
    if active_tab == "tab-economy":
        return economic_tab()
    if active_tab == "tab-backtest":
        return backtest_tab()
    if active_tab == "tab-alerts":
        return alerts_tab()
    if active_tab == "tab-crypto":
        return crypto_tab()
    if active_tab == "tab-bot":
        return bot_control_tab()
    if active_tab == "tab-ratings":
        return analyst_ratings_tab()
    if active_tab == "tab-dividends":
        return dividend_tracker_tab()
    if active_tab == "tab-options":
        return options_flow_tab()
    if active_tab == "tab-browse":
        return html.Div([
            dbc.Input(id="browse-search", placeholder="Search any ticker (e.g. AAPL, BTC-USD)...",
                      debounce=True,
                      style={"background": COLORS["panel"],
                             "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"], "marginBottom": "16px"}),
            html.Div(id="browse-content",
                     children=browse_tab_content(load_watchlist_symbols())),
        ])
    return html.Div()


_category_articles = {}
_category_summaries = {}
_category_filters = {}
_compare_list = []


def _get_category_articles(category):
    if category not in _category_articles:
        _category_articles[category] = get_news(CATEGORY_TICKERS[category], limit=20)
    return _category_articles[category]


def _get_category_summary(category, articles):
    if category not in _category_summaries and articles:
        headline_block = "\n".join(
            f"- {a['title']} (sentiment: {a['sentiment_label']})" for a in articles)
        prompt = (
            f"You are a senior financial analyst at a top investment bank. Analyze these headlines and provide a deep, professional market briefing.\n\n"
            f"**MARKET OVERVIEW**\n2-3 sentences on overall market mood.\n\n"
            f"**KEY THEMES**\n4-6 themes, each with detailed explanation.\n\n"
            f"**RISKS TO WATCH**\n2-3 specific risks or catalysts.\n\n"
            f"**BOTTOM LINE**\n1-2 sentences on what to pay attention to.\n\n"
            f"Only reference companies directly mentioned. Be specific and factual.\n\n"
            f"HEADLINES:\n{headline_block}"
        )
        _category_summaries[category] = generate_ai_text(prompt)
    return _category_summaries.get(category)


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input({"type": "cat-filter", "cat": ALL, "val": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def apply_category_filter(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if not triggered or not isinstance(triggered, dict):
        return dash.no_update
    category = triggered["cat"]
    _category_filters[category] = triggered["val"]
    articles = _get_category_articles(category)
    summary = _get_category_summary(category, articles)
    return category_content(category, articles, _category_filters[category], summary)


_cat_article_insights = {}


@callback(
    Output({"type": "cat-article-insight", "cat": ALL, "index": ALL}, "children"),
    Input({"type": "cat-accordion", "cat": ALL}, "active_item"),
    prevent_initial_call=True,
)
def cat_article_insight(active_items):
    outputs = [dash.no_update] * len(ctx.outputs_list)
    for accordion_idx, active_item in enumerate(active_items):
        if not active_item:
            continue
        parts = active_item.rsplit("-", 1)
        if len(parts) != 2:
            continue
        category, idx_str = parts
        try:
            idx = int(idx_str)
        except ValueError:
            continue
        articles = _get_category_articles(category)
        active_filter = _category_filters.get(category, "All")
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
        if idx >= len(filtered):
            continue
        a = filtered[idx]
        url = a.get("url", "")
        if url not in _cat_article_insights:
            prompt = (
                f"You are a financial analyst. Give a sharp 3-4 sentence take on why this article matters "
                f"for investors, the market implication, and any risk or opportunity.\n"
                f"Title: {a.get('title', '')}\n"
                f"Summary: {a.get('summary', 'N/A')}\n"
                f"Sentiment: {a.get('sentiment_label', '')}"
            )
            _cat_article_insights[url] = generate_ai_text(prompt)
        insight = _cat_article_insights.get(url, "")
        # Find matching output
        for out_idx, out in enumerate(ctx.outputs_list):
            if out["id"].get("cat") == category and out["id"].get("index") == idx:
                outputs[out_idx] = html.Div(dcc.Markdown(insight), style={
                    "background": "#0d1a13", "border": "1px solid #1a3d2a",
                    "borderLeft": "3px solid #4ade80", "borderRadius": "8px",
                    "padding": "14px 18px", "marginTop": "12px", "color": "#d1d5db"})
                break
    return outputs

@callback(
    Output("browse-content", "children"),
    Input("browse-search", "value"),
    prevent_initial_call=True,
)
def browse_search(search):
    return browse_tab_content(load_watchlist_symbols(), search or "")


@callback(
    Output("browse-content", "children", allow_duplicate=True),
    Output("watchlist-container", "children", allow_duplicate=True),
    Input({"type": "browse-toggle", "index": ALL}, "n_clicks"),
    State("browse-search", "value"),
    prevent_initial_call=True,
)
def browse_toggle(n_clicks, search):
    if not any(n_clicks):
        return dash.no_update, dash.no_update
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update, dash.no_update
    sym = triggered["index"]
    symbols = load_watchlist_symbols()
    if sym in symbols:
        symbols.remove(sym)
    else:
        symbols.append(sym)
    save_watchlist_symbols(symbols)
    return browse_tab_content(symbols, search or ""), watchlist_panel().children


@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input({"type": "browse-view", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def browse_view(n_clicks):
    if not any(n_clicks):
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        return triggered["index"]
    return dash.no_update


@callback(
    Output("news-subtab-content", "children"),
    Input("news-subtabs", "active_tab"),
)
def render_news_subtab(active_subtab):
    if active_subtab == "sub-news":
        feed, _ = fetch_news_dash()
        return news_grid(feed)
    if active_subtab == "sub-earnings":
        return earnings_tab()
    if active_subtab == "sub-insider":
        return insider_tab()
    if active_subtab == "sub-sec":
        return sec_tab()
    return html.Div()


_insider_insights = {}


@callback(
    Output({"type": "insider-insight", "index": dash.MATCH}, "children"),
    Input({"type": "insider-trade", "index": dash.MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def insider_insight(n_clicks):
    if not n_clicks:
        return dash.no_update
    idx = ctx.triggered_id["index"]
    trades = get_insider_trades()
    if idx >= len(trades):
        return dash.no_update
    t = trades[idx]
    key = f'{t.get("symbol")}_{t.get("name")}_{t.get("transactionDate")}_{t.get("change")}'
    if key not in _insider_insights:
        sym = t.get("symbol", "")
        name = t.get("name", "")
        shares = t.get("change", 0)
        price = t.get("transactionPrice", 0)
        action = "BUY" if shares > 0 else "SELL"
        value = abs(shares * price) if price else 0
        prompt = (
            f"You are a quantitative analyst at a hedge fund analyzing SEC Form 4 filings as alpha signals.\n\n"
            f"Transaction: {name} at {sym}, {action} {abs(shares):,} shares @ ${price:.2f} = ${value:,.0f} on {t.get('transactionDate', '')}\n\n"
            f"**SIGNAL TYPE**\nClassify: meaningful directional signal or noise (10b5-1 plan, tax, routine)?\n\n"
            f"**MAGNITUDE**\nIs the size significant relative to typical insider trades?\n\n"
            f"**HISTORICAL CONTEXT**\nBased on academic research (Seyhun 1986, Lakonishok & Lee 2001), what does this type of transaction historically predict?\n\n"
            f"**ALPHA SIGNAL RATING**\nRate: Strong Buy / Weak Buy / Neutral / Weak Sell / Strong Sell with reasoning."
        )
        _insider_insights[key] = generate_ai_text(prompt)
    return html.Div(dcc.Markdown(_insider_insights[key]), style={
        "background": "#0d1a13", "border": "1px solid #1a3d2a",
        "borderLeft": "3px solid #4ade80", "borderRadius": "8px",
        "padding": "14px 18px", "marginTop": "10px", "color": "#d1d5db"})


@callback(
    Output("selected-article", "data"),
    Input({"type": "news-card", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_article(n_clicks):
    if not any(n_clicks):
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        return triggered["index"]
    return dash.no_update


@callback(
    Output("selected-article", "data", allow_duplicate=True),
    Input("news-back-btn", "n_clicks"),
    prevent_initial_call=True,
)
def article_back(n):
    return None

@callback(
    Output("selected-ticker", "data"),
    Input({"type": "wl-item", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_ticker(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        return triggered["index"]
    return dash.no_update

@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input("ticker-back-btn", "n_clicks"),
    prevent_initial_call=True,
)
def go_back(n):
    return None

# ---------- CSS ----------
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
{%metas%}
<title>{%title%}</title>
{%favicon%}
{%css%}
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
body { font-family: 'Inter', sans-serif; background: #080c12; margin: 0; }
.tape-wrap { background: #0d1219; border-bottom: 1px solid #1a2130; overflow: hidden;
             white-space: nowrap; padding: 10px 0; }
.tape-track { display: inline-block; animation: scroll-tape 45s linear infinite; }
@keyframes scroll-tape { 0% { transform: translateX(0%); } 100% { transform: translateX(-50%); } }
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #0d1219; }
::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 4px; }
/* Dark dropdown */
#add-ticker-input .Select-control, .dash-dark-dropdown .Select-control { background-color: #11161f !important; border: 1px solid #2d3748 !important; color: #e2e8f0 !important; }
#add-ticker-input .Select-menu-outer, .dash-dark-dropdown .Select-menu-outer { background-color: #11161f !important; border: 1px solid #2d3748 !important; z-index: 9999 !important; }
#add-ticker-input .Select-option, #add-ticker-input .VirtualizedSelectOption { background-color: #11161f !important; color: #e2e8f0 !important; }
#add-ticker-input .Select-option:hover, #add-ticker-input .VirtualizedSelectFocusedOption, #add-ticker-input .Select-option.is-focused { background-color: #1a2130 !important; }
#add-ticker-input .Select-value-label, #add-ticker-input .Select-input > input { color: #e2e8f0 !important; }
#add-ticker-input .Select-placeholder { color: #64748b !important; }
#add-ticker-input .Select-arrow { border-color: #64748b transparent transparent !important; }
.Select-control { background: #0d1219 !important; border-color: #2d3748 !important; color: #e2e8f0 !important; }
.Select-menu-outer { background: #0d1219 !important; border-color: #2d3748 !important; }
.Select-option { background: #0d1219 !important; color: #e2e8f0 !important; }
.Select-option:hover, .Select-option.is-focused { background: #1a2130 !important; }
.Select-value-label { color: #e2e8f0 !important; }
.Select-placeholder { color: #64748b !important; }
.VirtualizedSelectOption { background: #0d1219 !important; color: #e2e8f0 !important; }
.VirtualizedSelectFocusedOption { background: #1a2130 !important; }
.dash-dropdown .Select-control { background-color: #0d1219 !important; }
.dash-dropdown .Select-menu-outer { background-color: #0d1219 !important; }
</style>
</head>
<body>
{%app_entry%}
<footer>
{%config%}
{%scripts%}
{%renderer%}
</footer>
</body>
</html>
'''



@callback(
    Output("watchlist-container", "children"),
    Input("add-ticker-btn", "n_clicks"),
    State("add-ticker-input", "value"),
    prevent_initial_call=True,
)
def add_ticker(n_clicks, value):
    sym = (value or "").strip().upper()
    if not sym:
        return dash.no_update
    symbols = load_watchlist_symbols()
    if sym not in symbols:
        try:
            info = yf.Ticker(sym).info
            if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose") or info.get("symbol"):
                symbols.append(sym)
                save_watchlist_symbols(symbols)
        except Exception:
            pass
    return get_watchlist_rows()


@callback(
    Output("watchlist-container", "children", allow_duplicate=True),
    Input({"type": "wl-remove", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def remove_ticker(n_clicks):
    if not any(n_clicks):
        return dash.no_update
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update
    sym = triggered["index"]
    symbols = load_watchlist_symbols()
    if sym in symbols:
        symbols.remove(sym)
        save_watchlist_symbols(symbols)
    return get_watchlist_rows()




_ticker_insights = {}
_ticker_period = {}


@callback(
    Output("ticker-chart", "figure"),
    Input({"type": "period-btn", "index": ALL, "sym": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def change_period(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update
    sym = triggered["sym"]
    label = triggered["index"]
    period_map = {"1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo",
                  "6M": "6mo", "YTD": "ytd", "5Y": "5y", "MAX": "max"}
    period = period_map.get(label, "1y")
    try:
        hist = yf.Ticker(sym).history(period=period)
        if hist.empty:
            return dash.no_update
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
        return fig
    except Exception:
        return dash.no_update
    try:
        hist = yf.Ticker(selected_ticker).history(period=period)
        if hist.empty:
            return dash.no_update
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
        return fig
    except Exception:
        return dash.no_update

@callback(
    Output("ticker-ai-analysis", "children"),
    Input("ticker-ai-analysis", "id"),
    State("selected-ticker", "data"),
    prevent_initial_call=True,
)
def ticker_ai(_, selected_ticker):
    if not selected_ticker:
        return dash.no_update
    if selected_ticker not in _ticker_insights:
        try:
            info = yf.Ticker(selected_ticker).info
            name = info.get("longName", selected_ticker)
            prompt = (
                f"You are a senior financial analyst. Provide a deep professional analysis of {selected_ticker} ({name}).\n\n"
                f"**COMPANY OVERVIEW**\nWhat does this company do and what is its market position?\n\n"
                f"**FINANCIAL HEALTH**\nAnalyze: P/E {info.get('trailingPE', 'N/A')}, "
                f"Revenue Growth {info.get('revenueGrowth', 'N/A')}, "
                f"Profit Margin {info.get('profitMargins', 'N/A')}, "
                f"Debt/Equity {info.get('debtToEquity', 'N/A')}.\n\n"
                f"**RISKS**\nKey risks facing this company.\n\n"
                f"**OPPORTUNITY**\nThe bull case for this stock.\n\n"
                f"**VERDICT**\nOverall assessment in 2-3 sentences."
            )
            _ticker_insights[selected_ticker] = generate_ai_text(prompt)
        except Exception:
            _ticker_insights[selected_ticker] = "Analysis unavailable."
    return html.Div([
        html.Div("AI ANALYSIS", style={"color": COLORS["text3"], "fontSize": "11px",
                                        "fontWeight": "600", "letterSpacing": "0.5px",
                                        "margin": "20px 0 12px"}),
        html.Div(dcc.Markdown(_ticker_insights[selected_ticker]), style={
            "background": "#0d1a13", "border": "1px solid #1a3d2a",
            "borderLeft": f"3px solid {COLORS['green']}", "borderRadius": "8px",
            "padding": "16px 20px", "color": "#d1d5db"}),
    ])




@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input({"type": "snapshot-tile", "sym": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def snapshot_click(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "sym" in triggered:
        return triggered["sym"]
    return dash.no_update



@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input("pf-add-btn", "n_clicks"),
    State("pf-symbol", "value"),
    State("pf-shares", "value"),
    State("pf-cost", "value"),
    prevent_initial_call=True,
)
def pf_add(n_clicks, symbol, shares, cost):
    if not symbol or not shares:
        return dash.no_update
    holdings = load_portfolio()
    sym = symbol.strip().upper()
    holdings = [h for h in holdings if h["symbol"] != sym]
    holdings.append({"symbol": sym, "shares": float(shares), "cost_basis": float(cost or 0)})
    save_portfolio(holdings)
    return portfolio_tab()


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input({"type": "pf-remove", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def pf_remove(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update
    sym = triggered["index"]
    holdings = [h for h in load_portfolio() if h["symbol"] != sym]
    save_portfolio(holdings)
    return portfolio_tab()



@callback(
    Output("map-subtab-content", "children"),
    Input("map-subtabs", "active_tab"),
)
def render_map_subtab(active_subtab):
    if active_subtab == "map-market":
        return market_treemap()
    if active_subtab == "map-etfs":
        return etf_treemap()
    if active_subtab == "map-portfolio":
        return portfolio_treemap()
    if active_subtab == "map-sectors":
        return sector_treemap()
    return html.Div()



@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input("market-treemap-graph", "clickData"),
    prevent_initial_call=True,
)
def market_map_click(clickData):
    if not clickData:
        return dash.no_update
    label = clickData["points"][0].get("label", "")
    # Only navigate if it's a ticker (not a sector parent)
    if label and label not in ["Market", "Technology", "Communication", "Consumer",
                                "Financials", "Healthcare", "Energy", "Industrials"]:
        return label
    return dash.no_update


@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input("etf-treemap-graph", "clickData"),
    prevent_initial_call=True,
)
def etf_map_click(clickData):
    if not clickData:
        return dash.no_update
    label = clickData["points"][0].get("label", "")
    if label and label not in ["ETFs", "Broad Market", "Sectors", "Tech/Growth",
                                "Bonds", "Commodities/Intl"]:
        return label
    return dash.no_update


@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input("portfolio-treemap-graph", "clickData"),
    prevent_initial_call=True,
)
def portfolio_map_click(clickData):
    if not clickData:
        return dash.no_update
    label = clickData["points"][0].get("label", "")
    if label and label != "Portfolio":
        return label
    return dash.no_update




@callback(
    Output("compare-results", "children"),
    Input("compare-add-btn", "n_clicks"),
    State("compare-input", "value"),
    prevent_initial_call=True,
)
def compare_add(n_clicks, value):
    global _compare_list
    if not value:
        return dash.no_update
    sym = value.strip().upper()
    if sym and sym not in _compare_list and len(_compare_list) < 4:
        try:
            info = yf.Ticker(sym).info
            if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"):
                _compare_list.append(sym)
        except Exception:
            pass
    return compare_results(_compare_list)


@callback(
    Output("compare-results", "children", allow_duplicate=True),
    Input({"type": "compare-remove", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def compare_remove(n_clicks):
    global _compare_list
    if not ctx.triggered:
        return dash.no_update
    val = ctx.triggered[0].get("value")
    if not val or val == 0:
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        sym = triggered["index"]
        if sym in _compare_list:
            _compare_list.remove(sym)
        return compare_results(_compare_list)
    return dash.no_update


@callback(
    Output("compare-results", "children", allow_duplicate=True),
    Input("compare-clear-btn", "n_clicks"),
    prevent_initial_call=True,
)
def compare_clear(n_clicks):
    global _compare_list
    _compare_list = []
    return compare_results(_compare_list)



@callback(
    Output("bt-results", "children"),
    Input("bt-run-btn", "n_clicks"),
    State("bt-allocation", "value"),
    State("bt-start", "value"),
    prevent_initial_call=True,
)
def run_bt(n_clicks, allocation_str, start_date):
    if not allocation_str:
        return html.Div("Enter an allocation first.", style={"color": COLORS["text2"]})
    try:
        weights = {}
        for part in allocation_str.split(","):
            sym, w = part.strip().split(":")
            weights[sym.strip().upper()] = float(w.strip()) / 100
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            return html.Div(f"Weights sum to {total*100:.0f}% — must sum to 100%.",
                           style={"color": COLORS["red"]})
        from dash_pages import run_backtest
        import plotly.graph_objects as go
        result = run_backtest(weights, start_date or "2015-01-01")
        if not result:
            return html.Div("Could not fetch data.", style={"color": COLORS["text2"]})
        
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
                          yaxis=dict(gridcolor=COLORS["border"], title="Value ($)"),
                          legend=dict(orientation="h"),
                          margin=dict(l=0, r=0, t=10, b=0), height=350)
        perf_chart = html.Div([
            html.Div("PORTFOLIO GROWTH vs SPY", style={"color": COLORS["text3"], "fontSize": "11px",
                                                        "fontWeight": "600", "marginBottom": "10px"}),
            dcc.Graph(figure=fig, config={"displayModeBar": False}),
        ], style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border']}",
                  "borderRadius": "10px", "padding": "16px 20px", "marginBottom": "16px"})

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

        annual = result["annual_returns"]
        bar_colors = [COLORS["green"] if v >= 0 else COLORS["red"] for v in annual.values]
        fig_ann = go.Figure()
        fig_ann.add_trace(go.Bar(x=[str(d.year) for d in annual.index], y=annual.values,
                                  marker_color=bar_colors,
                                  text=[f"{v:.1f}%" for v in annual.values],
                                  textposition="outside",
                                  textfont=dict(color=COLORS["text2"], size=11)))
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

        return html.Div([metric_cards, perf_chart, dd_chart, ann_chart])
    except Exception as e:
        return html.Div(f"Error: {e}", style={"color": COLORS["red"]})



@callback(
    Output("alerts-list", "children"),
    Input("alert-add-btn", "n_clicks"),
    State("alert-symbol", "value"),
    State("alert-condition", "value"),
    State("alert-target", "value"),
    prevent_initial_call=True,
)
def add_alert(n_clicks, symbol, condition, target):
    if not symbol or not target:
        return dash.no_update
    alerts = load_alerts()
    alerts.append({
        "symbol": symbol.strip().upper(),
        "condition": condition,
        "target": float(target),
        "triggered": False,
    })
    save_alerts(alerts)
    from dash_pages import alerts_tab
    return alerts_tab().children[1].children


@callback(
    Output("alerts-list", "children", allow_duplicate=True),
    Input({"type": "alert-remove", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def remove_alert(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if not triggered:
        return dash.no_update
    idx = triggered["index"]
    alerts = load_alerts()
    if idx < len(alerts):
        alerts.pop(idx)
        save_alerts(alerts)
    from dash_pages import alerts_tab
    return alerts_tab().children[1].children


@callback(
    Output("alert-notifications", "children"),
    Input("refresh-interval", "n_intervals"),
)
def check_alert_notifications(n):
    triggered = check_alerts()
    if not triggered:
        return []
    notifications = []
    for a in triggered:
        try:
            from plyer import notification
            notification.notify(
                title=f"Market Terminal Alert",
                message=f"{a['symbol']} {a['condition']} ${a['target']:.2f} — now at ${a['trigger_price']:.2f}",
                timeout=10,
            )
        except Exception:
            pass
        notifications.append(html.Div([
            html.Span(f"🔔 {a['symbol']} {a['condition']} ${a['target']:,.2f} — triggered @ ${a['trigger_price']:,.2f}",
                      style={"flex": "1", "color": "#fff", "fontWeight": "600"}),
        ], style={"background": "#16a34a", "border": "1px solid #4ade80",
                  "borderRadius": "8px", "padding": "12px 16px", "marginBottom": "6px",
                  "display": "flex", "alignItems": "center"}))
    return notifications



@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input({"type": "crypto-card", "sym": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def crypto_card_click(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "sym" in triggered:
        return triggered["sym"]
    return dash.no_update


@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input("crypto-treemap-graph", "clickData"),
    prevent_initial_call=True,
)
def crypto_map_click(clickData):
    if not clickData:
        return dash.no_update
    label = clickData["points"][0].get("label", "")
    crypto_names = list(__import__("dash_pages").CRYPTO_TICKERS.keys())
    if label in crypto_names:
        from dash_pages import CRYPTO_TICKERS
        return CRYPTO_TICKERS.get(label, label)
    return dash.no_update



@callback(
    Output("bot-save-status", "children"),
    Input("bot-save-btn", "n_clicks"),
    State("bot-strategy", "value"),
    State("bot-frequency", "value"),
    State("bot-drift", "value"),
    State("bot-maxpos", "value"),
    prevent_initial_call=True,
)
def bot_save_settings(n_clicks, strategy, frequency, drift, maxpos):
    config = load_bot_config()
    config["risk_tolerance"] = strategy
    config["rebalance_frequency"] = frequency
    config["drift_threshold"] = float(drift or 5)
    config["max_position_size"] = float(maxpos or 40)
    save_bot_config(config)
    return "✓ Configuration saved"


@callback(
    Output("bot-alloc-status", "children"),
    Input("bot-alloc-btn", "n_clicks"),
    State("bot-alloc-input", "value"),
    prevent_initial_call=True,
)
def bot_save_allocation(n_clicks, alloc_str):
    if not alloc_str:
        return "Enter an allocation first"
    try:
        alloc = {}
        for part in alloc_str.split(","):
            sym, w = part.strip().split(":")
            alloc[sym.strip().upper()] = float(w.strip())
        total = sum(alloc.values())
        if abs(total - 100) > 1:
            return f"⚠ Weights sum to {total:.0f}% — must sum to 100%"
        config = load_bot_config()
        config["target_allocation"] = alloc
        save_bot_config(config)
        return "✓ Allocation saved"
    except Exception as e:
        return f"Error: {e}"


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input("bot-start-btn", "n_clicks"),
    prevent_initial_call=True,
)
def bot_start(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    config = load_bot_config()
    config["active"] = True
    save_bot_config(config)
    return bot_control_tab()


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input("bot-stop-btn", "n_clicks"),
    prevent_initial_call=True,
)
def bot_stop(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    config = load_bot_config()
    config["active"] = False
    save_bot_config(config)
    return bot_control_tab()



@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input("bot-phase-next", "n_clicks"),
    prevent_initial_call=True,
)
def phase_next(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    config = load_bot_config()
    if config.get("phase", 1) < 3:
        config["phase"] = config.get("phase", 1) + 1
        if config["phase"] == 2:
            config["mode"] = "paper"
            from datetime import datetime
            config["paper_start_date"] = datetime.now().isoformat()
        elif config["phase"] == 3:
            config["mode"] = "live"
        save_bot_config(config)
    return bot_control_tab()


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input("bot-phase-back", "n_clicks"),
    prevent_initial_call=True,
)
def phase_back(n_clicks):
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    config = load_bot_config()
    if config.get("phase", 1) > 1:
        config["phase"] = config.get("phase", 1) - 1
        config["mode"] = "backtest" if config["phase"] == 1 else "paper"
        save_bot_config(config)
    return bot_control_tab()





_div_extra_symbols = []


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input("div-add-btn", "n_clicks"),
    State("div-add-input", "value"),
    prevent_initial_call=True,
)
def div_add(n_clicks, value):
    global _div_extra_symbols
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    if value:
        sym = value.strip().upper()
        if sym and sym not in _div_extra_symbols:
            _div_extra_symbols.append(sym)
    return dividend_tracker_tab(_div_extra_symbols)


@callback(
    Output("tab-content", "children", allow_duplicate=True),
    Input({"type": "div-remove", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def div_remove(n_clicks):
    global _div_extra_symbols
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        sym = triggered["index"]
        if sym in _div_extra_symbols:
            _div_extra_symbols.remove(sym)
    return dividend_tracker_tab(_div_extra_symbols)

if __name__ == "__main__":
    app.run(debug=False, port=8050)
