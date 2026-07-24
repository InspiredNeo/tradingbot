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

def watchlist_panel():
    data = get_watchlist_data()
    rows = []
    for sym, price, pct in data:
        color = COLORS["green"] if pct >= 0 else COLORS["red"]
        arrow = "▲" if pct >= 0 else "▼"
        rows.append(
            html.Div([
                html.Div([
                    html.Span(sym, style={"color": COLORS["text"], "fontWeight": "700",
                                          "fontSize": "13px", "fontFamily": FONT_MONO}),
                ]),
                html.Div([
                    html.Span(f"${price:.2f} ", style={"color": COLORS["text2"], "fontSize": "12px",
                                                        "fontFamily": FONT_MONO}),
                    html.Span(f"{arrow}{pct:+.2f}%", style={"color": color, "fontSize": "12px",
                                                             "fontWeight": "700"}),
                    html.Span(" ✕", id={"type": "wl-remove", "index": sym},
                              style={"color": COLORS["text3"], "cursor": "pointer",
                                     "marginLeft": "10px", "fontSize": "12px"}),
                ]),
            ],
            id={"type": "wl-item", "index": sym},
            n_clicks=0,
            style={
                "background": COLORS["panel"],
                "border": f"1px solid {COLORS['border2']}",
                "borderRadius": "8px",
                "padding": "10px 14px",
                "marginBottom": "6px",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "cursor": "pointer",
            })
        )
    return html.Div(rows, id="watchlist-container")

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
        dbc.InputGroup([
            dbc.Input(id="add-ticker-input", placeholder="Add ticker...",
                      style={"background": COLORS["panel"], "border": f"1px solid {COLORS['border2']}",
                             "color": COLORS["text"]}),
            dbc.Button("Add", id="add-ticker-btn", color="primary", size="sm"),
        ], className="mb-3"),
        watchlist_panel(),
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
)
def render_main(selected_ticker):
    if selected_ticker:
        return html.Div([
            dbc.Button("← Back", id="back-btn", color="secondary", size="sm", className="mb-3"),
            html.H3(selected_ticker, style={"color": COLORS["text"]}),
            html.P("Ticker detail view — chart and ratios coming in next step",
                   style={"color": COLORS["text2"]}),
        ])
    return html.Div([
        html.P("Main tabs coming in next step", style={"color": COLORS["text2"]}),
    ])

@callback(
    Output("selected-ticker", "data"),
    Input({"type": "wl-item", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_ticker(n_clicks):
    if not any(n_clicks):
        return dash.no_update
    triggered = ctx.triggered_id
    if triggered and "index" in triggered:
        return triggered["index"]
    return dash.no_update

@callback(
    Output("selected-ticker", "data", allow_duplicate=True),
    Input("back-btn", "n_clicks"),
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

if __name__ == "__main__":
    app.run(debug=True, port=8050)
