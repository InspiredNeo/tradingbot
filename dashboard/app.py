import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
import yfinance as yf
from google import genai
import groq as groq_lib
from ai_utils import generate_ai_text
from streamlit_autorefresh import st_autorefresh
from news_view import render_news_page

# Allow importing from the engine folder
sys.path.append(os.path.expanduser("~/tradingbot/engine"))
from data_sources import get_news

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
gemini_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=gemini_key)
groq_key = os.getenv("GROQ_API_KEY")
groq_client = groq_lib.Groq(api_key=groq_key)

st.set_page_config(page_title="Market Terminal", layout="wide")

TAPE_STOCKS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
TAPE_ETFS = ["SPY", "QQQ", "VOO", "VTI", "DIA"]
TAPE_INDICES = {"^GSPC": "S&P 500", "^DJI": "DOW", "^IXIC": "NASDAQ", "^FTSE": "FTSE 100", "^N225": "NIKKEI"}

CATEGORY_TICKERS = {
    "Stocks": "AAPL,MSFT,NVDA,GOOGL,AMZN,META,TSLA",
    "ETFs": "SPY,QQQ,VOO,VTI,DIA",
    "World": "^GSPC,^DJI,^IXIC,^FTSE,^N225"
}

if "articles" not in st.session_state:
    st.session_state.articles = {}
if "sentiment_filter" not in st.session_state:
    st.session_state.sentiment_filter = {}
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = None
if "article_insights" not in st.session_state:
    st.session_state.article_insights = {}
if "summary_insight" not in st.session_state:
    st.session_state.summary_insight = {}
if "last_update" not in st.session_state:
    st.session_state.last_update = None

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main { background-color: #080c12; }
header[data-testid="stHeader"] { background-color: #080c12; }
section[data-testid="stSidebar"] { background-color: #0d1219; border-right: 1px solid #1a2130; }

.tape-wrap {
    background-color: #0d1219;
    border-bottom: 1px solid #1a2130;
    overflow: hidden;
    white-space: nowrap;
    padding: 10px 0;
    margin: -1rem -1rem 20px -1rem;
}
.tape-track { display: inline-block; animation: scroll-tape 45s linear infinite; }
.tape-item { display: inline-block; margin-right: 36px; font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.tape-sym { color: #94a3b8; font-weight: 600; margin-right: 6px; }
.tape-up { color: #4ade80; }
.tape-down { color: #f87171; }
@keyframes scroll-tape { 0% { transform: translateX(0%); } 100% { transform: translateX(-50%); } }

.top-bar { display: flex; align-items: center; justify-content: space-between; padding: 4px 0 20px 0; border-bottom: 1px solid #1a2130; margin-bottom: 24px; }
.brand { font-size: 22px; font-weight: 700; color: #f1f5f9; letter-spacing: -0.5px; }
.brand span { color: #4b8bf5; }
.live-pulse {
    display: inline-flex; align-items: center; gap: 6px;
    background-color: #0f1a14; border: 1px solid #1a3d2a; color: #4ade80;
    padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
}
.pulse-dot { width: 7px; height: 7px; background-color: #4ade80; border-radius: 50%; animation: pulse 1.6s infinite; }
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(74,222,128,0.5); }
    70% { box-shadow: 0 0 0 6px rgba(74,222,128,0); }
    100% { box-shadow: 0 0 0 0 rgba(74,222,128,0); }
}

.metric-row { display: flex; gap: 12px; margin-bottom: 24px; }
.metric-box { flex: 1; background: linear-gradient(180deg, #11161f 0%, #0d1119 100%); border: 1px solid #1a2130; border-radius: 10px; padding: 16px 20px; }
.metric-label { color: #64748b; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; font-family: 'JetBrains Mono', monospace; }
.metric-value { font-size: 26px; font-weight: 700; margin-top: 4px; }

.section-title { font-size: 15px; font-weight: 600; color: #cbd5e1; margin: 8px 0 4px 0; }
.section-sub { color: #64748b; font-size: 12px; margin-bottom: 16px; }

.stButton>button { background-color: #141b26; color: #cbd5e1; border: 1px solid #263042; border-radius: 7px; font-weight: 500; font-size: 13px; padding: 8px 14px; }
.stButton>button:hover { border-color: #4b8bf5; color: #4b8bf5; background-color: #0f1622; }

.meta-row { font-size: 12px; color: #64748b; margin-top: 6px; font-family: 'JetBrains Mono', monospace; }
.ticker-chip { display: inline-block; background-color: #141b26; color: #93a4c3; padding: 3px 10px; border-radius: 12px; font-size: 10.5px; font-weight: 500; margin-right: 5px; border: 1px solid #263042; }
.source-chip { display: inline-block; background-color: #1a2332; color: #6b8bc4; padding: 3px 10px; border-radius: 12px; font-size: 10.5px; font-weight: 600; margin-right: 5px; border: 1px solid #2d4a6e; }
.sentiment-bullish { color: #4ade80; font-weight: 600; }
.sentiment-bearish { color: #f87171; font-weight: 600; }
.sentiment-neutral { color: #94a3b8; font-weight: 600; }

.ai-box { background-color: #0d1a13; border: 1px solid #1a3d2a; border-left: 3px solid #4ade80; border-radius: 6px; padding: 14px 18px; margin-top: 12px; font-size: 13.5px; line-height: 1.6; color: #d1d5db; }

div[data-testid="stExpander"] { background-color: #0d1119; border: 1px solid #1a2130; border-radius: 10px; margin-bottom: 8px; }
div[data-testid="stExpander"] summary { font-size: 14px; font-weight: 500; color: #e2e8f0; padding: 4px 0; }

.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid #1a2130; }
.stTabs [data-baseweb="tab"] { background-color: transparent; color: #64748b; font-weight: 500; padding: 10px 4px; }
.stTabs [aria-selected="true"] { color: #4b8bf5 !important; border-bottom: 2px solid #4b8bf5 !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("### Settings")
limit = st.sidebar.slider("Articles per category", 5, 50, 20)
auto_refresh_sec = st.sidebar.slider("Auto-refresh every (sec)", 30, 300, 60)
st.sidebar.divider()
if st.session_state.last_update:
    st.sidebar.caption(f"Last refreshed: {st.session_state.last_update}")

# --- Market Status ---
st.sidebar.markdown("### Market Status")
import zoneinfo

def get_market_status():
    ny = zoneinfo.ZoneInfo("America/New_York")
    now = datetime.now(ny)
    weekday = now.weekday()  # 0=Monday, 6=Sunday
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

status, status_msg = get_market_status()
status_color = "#4ade80" if status == "open" else "#f59e0b" if status == "pre" else "#f87171"
st.sidebar.markdown(f"""
<div style="background:#0d1219; border:1px solid #1a2130; border-left: 3px solid {status_color};
border-radius:8px; padding:10px 14px; margin-bottom:8px;">
<span style="color:{status_color}; font-weight:700; font-size:13px;">● {status_msg}</span>
</div>
""", unsafe_allow_html=True)

# --- Watchlist ---
st.sidebar.markdown("### Watchlist")

WATCHLIST_FILE = os.path.expanduser("~/tradingbot/config/watchlist.json")

def load_watchlist_symbols():
    try:
        if os.path.exists(WATCHLIST_FILE):
            import json
            with open(WATCHLIST_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return ["AAPL", "MSFT", "NVDA", "TSLA", "SPY", "QQQ", "BND", "VTI"]

def save_watchlist_symbols(symbols):
    try:
        import json
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(symbols, f)
    except Exception:
        pass

@st.cache_data(ttl=60)
def get_watchlist(symbols_tuple):
    symbols = list(symbols_tuple)
    try:
        data = yf.download(symbols, period="2d", progress=False, group_by="ticker")
        results = []
        for sym in symbols:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = float(closes.iloc[-2]), float(closes.iloc[-1])
                    pct = ((curr - prev) / prev) * 100
                    results.append((sym, curr, pct))
            except Exception:
                continue
        return results
    except Exception:
        return []

wl_symbols = load_watchlist_symbols()
watchlist = get_watchlist(tuple(wl_symbols))

# Add ticker input
add_col, btn_col = st.sidebar.columns([2, 1])
with add_col:
    new_ticker = st.text_input("", placeholder="Add ticker...", label_visibility="collapsed", key="add_ticker_input")
with btn_col:
    if st.button("Add", key="add_ticker_btn", use_container_width=True):
        ticker_upper = new_ticker.strip().upper()
        if ticker_upper and ticker_upper not in wl_symbols:
            # Validate ticker is real
            try:
                test = yf.Ticker(ticker_upper)
                info = test.info
                if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"):
                    wl_symbols.append(ticker_upper)
                    save_watchlist_symbols(wl_symbols)
                    get_watchlist.clear()
                    st.rerun()
                else:
                    st.sidebar.error(f"Could not find ticker: {ticker_upper}")
            except Exception:
                st.sidebar.error(f"Invalid ticker: {ticker_upper}")
        elif ticker_upper in wl_symbols:
            st.sidebar.warning(f"{ticker_upper} already in watchlist")

if watchlist:
    st.sidebar.markdown("""
<style>
section[data-testid="stSidebar"] button[kind="secondary"] {
    background: #0d1219 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: JetBrains Mono, monospace !important;
    font-weight: 700 !important;
    font-size: 13px !important;
}
section[data-testid="stSidebar"] button[kind="secondary"]:hover {
    border-color: #4b8bf5 !important;
    color: #4b8bf5 !important;
    background: #0f1622 !important;
}
</style>
""", unsafe_allow_html=True)
    for sym, price, pct in watchlist:
        color = "#4ade80" if pct >= 0 else "#f87171"
        arrow = "▲" if pct >= 0 else "▼"
        col1, col2, col3 = st.sidebar.columns([1, 1.4, 0.5])
        with col1:
            if st.button(sym, key=f"wl_{sym}", use_container_width=True):
                st.session_state.selected_ticker = sym
                st.rerun()
        with col2:
            st.markdown(
                f'<div style="padding:10px 0; line-height:1;">'
                f'<span style="color:#94a3b8; font-size:12px; font-family:JetBrains Mono,monospace;">${price:.2f} </span>'
                f'<span style="color:{color}; font-size:12px; font-weight:700;">{arrow}{pct:+.2f}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )
        with col3:
            if st.button("✕", key=f"rm_{sym}", use_container_width=True):
                wl_symbols.remove(sym)
                save_watchlist_symbols(wl_symbols)
                get_watchlist.clear()
                st.rerun()

# --- Bot Status ---
st.sidebar.divider()
st.sidebar.markdown("### Bot Status")

def get_bot_status():
    try:
        sys.path.append(os.path.expanduser("~/tradingbot/engine"))
        status_file = os.path.expanduser("~/tradingbot/engine/bot_status.json")
        if os.path.exists(status_file):
            import json
            with open(status_file) as f:
                return json.load(f)
    except Exception:
        pass
    return None

bot = get_bot_status()
if bot:
    st.sidebar.markdown(f"""
    <div style="background:#0d1219; border:1px solid #1a2130; border-radius:8px; padding:10px 14px;">
        <div style="color:#4ade80; font-size:12px; font-weight:700;">● RUNNING</div>
        <div style="color:#94a3b8; font-size:11px; margin-top:4px;">Last rebalance: {bot.get('last_rebalance', 'N/A')}</div>
        <div style="color:#94a3b8; font-size:11px;">Next rebalance: {bot.get('next_rebalance', 'N/A')}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.sidebar.markdown("""
    <div style="background:#0d1219; border:1px solid #1a2130; border-radius:8px; padding:10px 14px;">
        <div style="color:#f87171; font-size:12px; font-weight:700;">● NOT RUNNING</div>
        <div style="color:#64748b; font-size:11px; margin-top:4px;">Engine offline</div>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=60)
def get_tape_data():
    all_symbols = TAPE_STOCKS + TAPE_ETFS + list(TAPE_INDICES.keys())
    results = []
    try:
        data = yf.download(all_symbols, period="2d", progress=False, group_by="ticker")
        for sym in all_symbols:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) >= 2:
                    prev, curr = closes.iloc[-2], closes.iloc[-1]
                    pct = ((curr - prev) / prev) * 100
                    label = TAPE_INDICES.get(sym, sym)
                    results.append((label, curr, pct))
            except Exception:
                continue
    except Exception:
        pass
    return results


def render_ticker_tape():
    data = get_tape_data()
    if not data:
        return
    items = ""
    for label, price, pct in data:
        cls = "tape-up" if pct >= 0 else "tape-down"
        arrow = "▲" if pct >= 0 else "▼"
        items += f'<span class="tape-item"><span class="tape-sym">{label}</span>{price:.2f} <span class="{cls}">{arrow} {pct:+.2f}%</span></span>'
    st.markdown(f'<div class="tape-wrap"><div class="tape-track">{items}{items}</div></div>', unsafe_allow_html=True)


def sentiment_span(label, score):
    cls = "sentiment-neutral"
    if "Bullish" in label:
        cls = "sentiment-bullish"
    elif "Bearish" in label:
        cls = "sentiment-bearish"
    return f'<span class="{cls}">{label} ({score})</span>'


def get_article_insight(article):
    key = article["url"]
    if key in st.session_state.article_insights:
        return st.session_state.article_insights[key]
    prompt = f"""You are a financial analyst. Analyze this single news article and give a short,
sharp take (3-4 sentences max) on why it matters for investors, what the market implication is,
and any risk or opportunity it signals. Be direct and specific, no filler.

Title: {article['title']}
Summary: {article.get('summary', 'N/A')}
Overall sentiment: {article['sentiment_label']} ({article['sentiment_score']})
Source: {article['source']}
"""
    result_text = generate_ai_text(prompt)
    st.session_state.article_insights[key] = result_text
    return result_text


def render_category(category, tickers):
    if category not in st.session_state.articles:
        with st.spinner(f"Loading {category}..."):
            st.session_state.articles[category] = get_news(tickers, limit=limit)
            st.session_state.last_update = datetime.now().strftime("%H:%M:%S")

    articles = st.session_state.articles[category]

    if not articles:
        st.info("No articles available right now from any source.")
        return

    bullish = sum(1 for a in articles if "Bullish" in a["sentiment_label"])
    bearish = sum(1 for a in articles if "Bearish" in a["sentiment_label"])
    neutral = len(articles) - bullish - bearish

    # --- Clickable filter buttons ---
    current_filter = st.session_state.sentiment_filter.get(category, "All")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button(f"📊 ALL  {len(articles)}", key=f"filter_all_{category}",
                     use_container_width=True):
            st.session_state.sentiment_filter[category] = "All"
            st.rerun()
    with col2:
        if st.button(f"🟢 BULLISH  {bullish}", key=f"filter_bull_{category}",
                     use_container_width=True):
            st.session_state.sentiment_filter[category] = "Bullish"
            st.rerun()
    with col3:
        if st.button(f"🔴 BEARISH  {bearish}", key=f"filter_bear_{category}",
                     use_container_width=True):
            st.session_state.sentiment_filter[category] = "Bearish"
            st.rerun()
    with col4:
        if st.button(f"⚪ NEUTRAL  {neutral}", key=f"filter_neu_{category}",
                     use_container_width=True):
            st.session_state.sentiment_filter[category] = "Neutral"
            st.rerun()

    # Show which filter is active
    if current_filter != "All":
        st.caption(f"Filtering by: {current_filter} — click ALL to reset")
    

    if category not in st.session_state.summary_insight:
        with st.spinner("Generating market summary..."):
            headline_block = "\n".join(f"- {a['title']} (sentiment: {a['sentiment_label']})" for a in articles)
            prompt = (
                f"You are a senior financial analyst at a top investment bank. Analyze these headlines and provide a deep, professional market briefing.\n\n"
                f"**MARKET OVERVIEW**\n"
                f"2-3 sentences summarizing the overall market mood and macro environment.\n\n"
                f"**KEY THEMES**\n"
                f"- Theme 1: detailed explanation of what is driving it and why it matters\n"
                f"- Theme 2: detailed explanation\n"
                f"- Theme 3: detailed explanation\n"
                f"(4-6 themes total)\n\n"
                f"**RISKS TO WATCH**\n"
                f"- 2-3 specific risks or catalysts that could move markets\n\n"
                f"**BOTTOM LINE**\n"
                f"1-2 sentences on what investors should be paying attention to right now.\n\n"
                f"Only reference companies or tickers directly mentioned in the headlines. Be specific, factual, and professional.\n\n"
                f"HEADLINES:\n{headline_block}"
            )
            result_text = generate_ai_text(prompt)
            st.session_state.summary_insight[category] = result_text

    if st.session_state.summary_insight.get(category):
        st.markdown(f'<div class="ai-box">{st.session_state.summary_insight[category]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Headlines</div><div class="section-sub">Click an article to expand and generate an AI take on it.</div>', unsafe_allow_html=True)

    if current_filter == "Bullish":
        filtered = [a for a in articles if "Bullish" in a["sentiment_label"]]
    elif current_filter == "Bearish":
        filtered = [a for a in articles if "Bearish" in a["sentiment_label"]]
    elif current_filter == "Neutral":
        filtered = [a for a in articles if "Bullish" not in a["sentiment_label"] and "Bearish" not in a["sentiment_label"]]
    else:
        filtered = articles

    for i, a in enumerate(filtered):
        chips = " ".join(f'<span class="ticker-chip">{t}</span>' for t in a.get("tickers", []))
        with st.expander(a["title"]):
            st.markdown(
                f'<div class="meta-row">{a["source"]} &nbsp;|&nbsp; <span class="source-chip">{a["data_source"]}</span> &nbsp;|&nbsp; {sentiment_span(a["sentiment_label"], a["sentiment_score"])} &nbsp;|&nbsp; {chips}</div>',
                unsafe_allow_html=True
            )
            st.write("")
            img_col, text_col = st.columns([1, 3])
            with img_col:
                if a.get("banner_image"):
                    st.image(a["banner_image"], use_container_width=True)
            with text_col:
                if a.get("summary"):
                    st.write(a["summary"])
                if a.get("url"):
                    st.markdown(f"[Read full article]({a['url']})")

                if a["url"] not in st.session_state.article_insights:
                    with st.spinner("Analyzing..."):
                        get_article_insight(a)
                if a["url"] in st.session_state.article_insights:
                    st.markdown(f'<div class="ai-box">{st.session_state.article_insights[a["url"]]}</div>', unsafe_allow_html=True)



@st.cache_data(ttl=300)
def get_ticker_detail(sym):
    """Fetch price history and key ratios for a ticker."""
    try:
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="1y")
        info = ticker.info
        return hist, info
    except Exception:
        return None, {}

def render_ticker_detail(sym):
    """Full page ticker detail view with chart and ratios."""
    if st.button("← Back"):
        st.session_state.selected_ticker = None
        st.rerun()

    hist, info = get_ticker_detail(sym)

    # Header
    name = info.get("longName", sym)
    price = info.get("currentPrice") or info.get("regularMarketPrice", 0)
    prev_close = info.get("previousClose", 0)
    change = price - prev_close if price and prev_close else 0
    change_pct = (change / prev_close * 100) if prev_close else 0
    color = "#4ade80" if change >= 0 else "#f87171"
    arrow = "▲" if change >= 0 else "▼"

    st.markdown(f"""
<div style="background:#0d1219; border:1px solid #1a2130; border-radius:12px; padding:20px 24px; margin-bottom:20px;">
    <div style="color:#64748b; font-size:12px; font-weight:600;">{name}</div>
    <div style="display:flex; align-items:baseline; gap:16px; margin-top:6px;">
        <span style="color:#e2e8f0; font-size:36px; font-weight:800; font-family:JetBrains Mono,monospace;">{sym}</span>
        <span style="color:#e2e8f0; font-size:28px; font-weight:700;">${price:,.2f}</span>
        <span style="color:{color}; font-size:18px; font-weight:700;">{arrow} {change:+.2f} ({change_pct:+.2f}%)</span>
    </div>
</div>""", unsafe_allow_html=True)

    # Time range selector
    periods = {"1D": "1d", "1W": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "YTD": "ytd", "1Y": "1y", "5Y": "5y"}
    if "chart_period" not in st.session_state:
        st.session_state.chart_period = "1Y"
    cols = st.columns(len(periods))
    for col, (label, period) in zip(cols, periods.items()):
        with col:
            if st.button(label, key=f"period_{label}_{sym}", use_container_width=True):
                st.session_state.chart_period = label
                st.rerun()

    # Chart
    selected_period = periods.get(st.session_state.chart_period, "1y")
    try:
        chart_hist = yf.Ticker(sym).history(period=selected_period)
        if not chart_hist.empty:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=chart_hist.index,
                y=chart_hist["Close"],
                mode="lines",
                line=dict(color="#4b8bf5", width=2),
                fill="tozeroy",
                fillcolor="rgba(75,139,245,0.1)"
            ))
            fig.update_layout(
                paper_bgcolor="#0d1219",
                plot_bgcolor="#0d1219",
                font=dict(color="#94a3b8"),
                xaxis=dict(gridcolor="#1a2130", showgrid=True),
                yaxis=dict(gridcolor="#1a2130", showgrid=True),
                margin=dict(l=0, r=0, t=0, b=0),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Chart data unavailable.")

    # Key Ratios
    st.markdown('<div style="color:#64748b; font-size:11px; font-weight:600; letter-spacing:0.5px; margin:20px 0 12px 0;">KEY RATIOS</div>', unsafe_allow_html=True)
    ratios = [
        ("P/E Ratio", info.get("trailingPE")),
        ("Forward P/E", info.get("forwardPE")),
        ("P/B Ratio", info.get("priceToBook")),
        ("EV/EBITDA", info.get("enterpriseToEbitda")),
        ("Profit Margin", info.get("profitMargins")),
        ("Revenue Growth", info.get("revenueGrowth")),
        ("Debt/Equity", info.get("debtToEquity")),
        ("ROE", info.get("returnOnEquity")),
        ("Market Cap", info.get("marketCap")),
        ("52W High", info.get("fiftyTwoWeekHigh")),
        ("52W Low", info.get("fiftyTwoWeekLow")),
        ("Div Yield", info.get("dividendYield")),
    ]
    cols = st.columns(4)
    for i, (label, val) in enumerate(ratios):
        with cols[i % 4]:
            if val is None:
                display = "N/A"
            elif label in ["Profit Margin", "Revenue Growth", "ROE", "Div Yield"]:
                display = f"{val*100:.2f}%"
            elif label == "Market Cap":
                display = f"${val/1e9:.2f}B" if val > 1e9 else f"${val/1e6:.0f}M"
            else:
                display = f"{val:.2f}"
            st.markdown(f"""
<div style="background:#0d1219; border:1px solid #1a2130; border-radius:8px; padding:12px 16px; margin-bottom:8px;">
    <div style="color:#64748b; font-size:11px; font-weight:600;">{label}</div>
    <div style="color:#e2e8f0; font-size:18px; font-weight:700; margin-top:4px;">{display}</div>
</div>""", unsafe_allow_html=True)

    # AI Analysis
    st.markdown('<div style="color:#64748b; font-size:11px; font-weight:600; letter-spacing:0.5px; margin:20px 0 12px 0;">AI ANALYSIS</div>', unsafe_allow_html=True)
    ai_key = f"ticker_insight_{sym}"
    if ai_key not in st.session_state:
        with st.spinner(f"Analyzing {sym}..."):
            prompt = (
                f"You are a senior financial analyst. Provide a deep professional analysis of {sym} ({name}).\n\n"
                f"**COMPANY OVERVIEW**\nWhat does this company do and what is its market position?\n\n"
                f"**FINANCIAL HEALTH**\nAnalyze these key metrics: P/E {info.get('trailingPE', 'N/A')}, "
                f"Revenue Growth {info.get('revenueGrowth', 'N/A')}, Profit Margin {info.get('profitMargins', 'N/A')}, "
                f"Debt/Equity {info.get('debtToEquity', 'N/A')}.\n\n"
                f"**RISKS**\nWhat are the key risks facing this company?\n\n"
                f"**OPPORTUNITY**\nWhat is the bull case for this stock?\n\n"
                f"**VERDICT**\nOverall assessment in 2-3 sentences."
            )
            st.session_state[ai_key] = generate_ai_text(prompt)
    if st.session_state.get(ai_key):
        st.markdown(f'<div class="ai-box">{st.session_state[ai_key]}</div>', unsafe_allow_html=True)

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

def render_browse_tab():
    wl_symbols = load_watchlist_symbols()
    search = st.text_input("Search by ticker (e.g. AAPL, MSFT, BTC-USD)", placeholder="Type any ticker...", key="browse_search")

    def render_ticker_card(sym):
        in_watchlist = sym in wl_symbols
        border = "#4b8bf5" if in_watchlist else "#1a2130"
        st.markdown(f"""
<div style="background:#0d1219; border:1px solid {border}; border-radius:8px;
padding:10px 14px; margin-bottom:8px; text-align:center;">
    <div style="color:#e2e8f0; font-weight:700; font-size:14px;
    font-family:JetBrains Mono,monospace;">{sym}</div>
    {"<div style='color:#4b8bf5; font-size:10px;'>IN WATCHLIST</div>" if in_watchlist else ""}
</div>""", unsafe_allow_html=True)
        btn1, btn2 = st.columns(2)
        with btn1:
            if st.button("View", key=f"browse_view_{sym}", use_container_width=True):
                st.session_state.selected_ticker = sym
                st.rerun()
        with btn2:
            if in_watchlist:
                if st.button("✕ Remove", key=f"browse_rm_{sym}", use_container_width=True):
                    wl_symbols.remove(sym)
                    save_watchlist_symbols(wl_symbols)
                    get_watchlist.clear()
                    st.rerun()
            else:
                if st.button("+ Add", key=f"browse_add_{sym}", use_container_width=True):
                    wl_symbols.append(sym)
                    save_watchlist_symbols(wl_symbols)
                    get_watchlist.clear()
                    st.rerun()

    # If searching, try to find in lists first, then fetch live
    if search:
        search_upper = search.strip().upper()
        matches = [s for s in BROWSE_STOCKS + BROWSE_ETFS if search_upper in s]
        if matches:
            cols_per_row = 4
            for row_start in range(0, len(matches), cols_per_row):
                row = matches[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, sym in zip(cols, row):
                    with col:
                        render_ticker_card(sym)
        else:
            # Try live lookup
            try:
                test = yf.Ticker(search_upper)
                info = test.info
                if info.get("regularMarketPrice") or info.get("currentPrice") or info.get("previousClose"):
                    st.markdown(f"**Found: {search_upper}** — {info.get('longName', '')}")
                    render_ticker_card(search_upper)
                else:
                    st.info(f"No results found for '{search}'")
            except Exception:
                st.info(f"No results found for '{search}'")
    else:
        tab_stocks, tab_etfs = st.tabs(["📈 Stocks", "📊 ETFs"])
        with tab_stocks:
            cols_per_row = 4
            for row_start in range(0, len(BROWSE_STOCKS), cols_per_row):
                row = BROWSE_STOCKS[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, sym in zip(cols, row):
                    with col:
                        render_ticker_card(sym)
        with tab_etfs:
            cols_per_row = 4
            for row_start in range(0, len(BROWSE_ETFS), cols_per_row):
                row = BROWSE_ETFS[row_start:row_start + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, sym in zip(cols, row):
                    with col:
                        render_ticker_card(sym)


render_ticker_tape()
st.markdown(f"""
<div class="top-bar">
    <div class="brand">Market <span>Terminal</span></div>
    <div class="live-pulse"><span class="pulse-dot"></span> LIVE - updates every {auto_refresh_sec}s</div>
</div>""", unsafe_allow_html=True)

# Show ticker detail view if a ticker is selected
if st.session_state.selected_ticker:
    render_ticker_detail(st.session_state.selected_ticker)
else:
    tab_labels = ["📰 News"] + list(CATEGORY_TICKERS.keys()) + ["Browse"]
    tabs = st.tabs(tab_labels)
    for label, tab in zip(tab_labels, tabs):
        with tab:
            if label == "📰 News":
                render_news_page()
            elif label == "Browse":
                render_browse_tab()
            else:
                render_category(label, CATEGORY_TICKERS[label])
