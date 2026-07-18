"""
news_view.py — CNN-style news page for the Market Terminal
"""

import os
import html
from datetime import datetime, timezone

import requests
import streamlit as st
import yfinance as yf
from dotenv import load_dotenv

# --- Config ---
load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")

AV_URL = "https://www.alphavantage.co/query"
CACHE_TTL_SECONDS = 1800

SENTIMENT_COLORS = {
    "Bullish": "#12b76a",
    "Somewhat-Bullish": "#4caf50",
    "Neutral": "#8a8f98",
    "Somewhat-Bearish": "#f59e0b",
    "Bearish": "#ef4444",
}


# --- Data ---
@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_news(limit=50):
    if not ALPHA_VANTAGE_API_KEY:
        return [], "No Alpha Vantage key."
    try:
        resp = requests.get(AV_URL, params={
            "function": "NEWS_SENTIMENT",
            "apikey": ALPHA_VANTAGE_API_KEY,
            "limit": limit,
            "sort": "LATEST",
        }, timeout=15)
        data = resp.json()
        if "feed" in data and len(data["feed"]) > 0:
            return data["feed"], "Alpha Vantage"
    except Exception:
        pass

    # Finnhub fallback
    try:
        if FINNHUB_API_KEY:
            resp = requests.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": FINNHUB_API_KEY},
                timeout=15,
            )
            raw = resp.json()
            if isinstance(raw, list) and len(raw) > 0:
                feed = []
                for a in raw[:limit]:
                    feed.append({
                        "title": a.get("headline", ""),
                        "summary": a.get("summary", ""),
                        "url": a.get("url", "#"),
                        "banner_image": a.get("image", ""),
                        "source": a.get("source", ""),
                        "time_published": _finnhub_time(a.get("datetime", 0)),
                        "overall_sentiment_label": "Neutral",
                        "overall_sentiment_score": 0,
                    })
                return feed, "Finnhub"
    except Exception:
        pass

    # Twelve Data fallback
    try:
        if TWELVE_DATA_API_KEY:
            resp = requests.get(
                "https://api.twelvedata.com/news",
                params={"apikey": TWELVE_DATA_API_KEY, "count": limit},
                timeout=15,
            )
            data = resp.json()
            raw = data.get("data") or data.get("news") or []
            if raw:
                feed = []
                for a in raw[:limit]:
                    feed.append({
                        "title": a.get("title", ""),
                        "summary": a.get("description", ""),
                        "url": a.get("url", "#"),
                        "banner_image": a.get("thumbnail", ""),
                        "source": a.get("source", ""),
                        "time_published": _twelve_time(a.get("published_at", "")),
                        "overall_sentiment_label": "Neutral",
                        "overall_sentiment_score": 0,
                    })
                return feed, "Twelve Data"
    except Exception:
        pass

    return [], None


@st.cache_data(ttl=60)
def get_snapshot():
    symbols = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "VIX": "^VIX",
        "Gold": "GC=F",
        "Oil": "CL=F",
        "10Y Yield": "^TNX",
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


# --- Helpers ---
def _finnhub_time(unix_ts):
    try:
        return datetime.utcfromtimestamp(int(unix_ts)).strftime("%Y%m%dT%H%M%S")
    except Exception:
        return ""


def _twelve_time(iso_str):
    try:
        dt = datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y%m%dT%H%M%S")
    except Exception:
        return ""


def _time_ago(published):
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


def _clean(text, limit=200):
    return html.escape((text or "").strip()[:limit])


def _pill(article):
    label = article.get("overall_sentiment_label", "Neutral")
    color = SENTIMENT_COLORS.get(label, "#8a8f98")
    return f'<span class="pill" style="background:{color}">{html.escape(label)}</span>'


# --- Styling ---
CSS = """
<style>
.news-wrap { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
.news-wrap a { text-decoration: none; color: inherit; }
.pill {
  display: inline-block; color: #fff; font-size: 11px; font-weight: 700;
  letter-spacing: .3px; padding: 3px 9px; border-radius: 999px; text-transform: uppercase;
}
.meta { color: #6b7280; font-size: 12.5px; margin-top: 6px; }
.hero {
  display: block; position: relative; border-radius: 14px; overflow: hidden;
  margin-bottom: 22px; box-shadow: 0 6px 24px rgba(0,0,0,.18);
}
.hero img { width: 100%; height: 320px; object-fit: cover; object-position: top; display: block; }
.hero-overlay {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 26px 26px 22px;
  background: linear-gradient(to top, rgba(0,0,0,.85) 10%, rgba(0,0,0,.35) 55%, rgba(0,0,0,0) 100%);
}
.hero-overlay h2 { color: #fff; font-size: 27px; line-height: 1.2; margin: 10px 0 4px; font-weight: 800; }
.hero-overlay .meta { color: #d1d5db; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
@media (max-width: 1100px) { .grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px)  { .grid { grid-template-columns: 1fr; } }
.card {
  display: block; border-radius: 12px; overflow: hidden;
  background: #1a2332; border: 1px solid #2d3748;
  box-shadow: 0 2px 10px rgba(0,0,0,.12); transition: transform .12s ease, box-shadow .12s ease;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(0,0,0,.20); }
.card img { width: 100%; height: 140px; object-fit: cover; object-position: top; display: block; }
.card-body { padding: 14px 15px 16px; }
.card-body h3 { color: #e5e7eb; font-size: 16px; line-height: 1.3; margin: 9px 0 6px; font-weight: 700; }
.card-body p  { color: #9aa4b2; font-size: 13px; line-height: 1.45; margin: 0; }
</style>
"""


# --- Renderers ---
def _hero_html(a):
    return (
        f'<a class="hero" href="{a.get("url", "#")}" target="_blank">'
        f'<img src="{a.get("banner_image", "")}">'
        f'<div class="hero-overlay">{_pill(a)}'
        f'<h2>{_clean(a.get("title"), 150)}</h2>'
        f'<div class="meta">{html.escape(a.get("source", ""))} &middot; {_time_ago(a.get("time_published", ""))}</div>'
        f'</div></a>'
    )


def _card_html(a):
    return (
        f'<a class="card" href="{a.get("url", "#")}" target="_blank">'
        f'<img src="{a.get("banner_image", "")}">'
        f'<div class="card-body">{_pill(a)}'
        f'<h3>{_clean(a.get("title"), 130)}</h3>'
        f'<p>{_clean(a.get("summary"), 150)}&hellip;</p>'
        f'<div class="meta">{html.escape(a.get("source", ""))} &middot; {_time_ago(a.get("time_published", ""))}</div>'
        f'</div></a>'
    )


def render_top_news(feed):
    # Filter out placeholder/logo images by checking for common bad patterns
    def good_image(a):
        img = a.get("banner_image", "")
        if not img:
            return False
        bad = ["logo", "icon", "avatar", "placeholder", "default", "blank"]
        return not any(b in img.lower() for b in bad)
    with_img = [a for a in feed if good_image(a)]
    if not with_img:
        st.info("No articles with images available right now.")
        return
    hero = with_img[0]
    rest = with_img[1:8]
    grid = "".join(_card_html(a) for a in rest)
    st.markdown(
        f'<div class="news-wrap">{_hero_html(hero)}<div class="grid">{grid}</div></div>',
        unsafe_allow_html=True,
    )

@st.cache_data(ttl=3600)
def get_earnings():
    try:
        key = os.getenv("FINNHUB_API_KEY")
        from datetime import date, timedelta
        today = date.today()
        to = today + timedelta(days=7)
        resp = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={
                "from": today.strftime("%Y-%m-%d"),
                "to": to.strftime("%Y-%m-%d"),
                "token": key
            },
            timeout=15
        )
        data = resp.json()
        return data.get("earningsCalendar", [])
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_economic_calendar():
    try:
        key = os.getenv("FINNHUB_API_KEY")
        from datetime import date, timedelta
        today = date.today()
        to = today + timedelta(days=14)
        resp = requests.get(
            "https://finnhub.io/api/v1/calendar/economic",
            params={
                "from": today.strftime("%Y-%m-%d"),
                "to": to.strftime("%Y-%m-%d"),
                "token": key
            },
            timeout=15
        )
        data = resp.json()
        return data.get("economicCalendar", [])
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_sec_filings():
    try:
        key = os.getenv("FINNHUB_API_KEY")
        # Get filings for your watched tickers
        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
                   "SPY", "QQQ", "VOO", "VTI", "BND"]
        all_filings = []
        for sym in symbols[:6]:  # limit to 6 to avoid rate limiting
            try:
                resp = requests.get(
                    "https://finnhub.io/api/v1/stock/filings",
                    params={"symbol": sym, "token": key},
                    timeout=10
                )
                filings = resp.json()
                if isinstance(filings, list):
                    for f in filings[:3]:
                        f["symbol"] = sym
                        all_filings.append(f)
            except Exception:
                continue
        # Sort by date descending
        all_filings.sort(key=lambda x: x.get("filedDate", ""), reverse=True)
        return all_filings[:30]
    except Exception:
        return []


def render_earnings():
    earnings = get_earnings()
    if not earnings:
        st.info("No earnings data available right now.")
        return

    # Filter to only show entries with estimates
    earnings = [e for e in earnings if e.get("epsEstimate") is not None]

    # Priority tickers first
    priority = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
                "SPY", "QQQ", "GME", "SCHW", "GM", "NOC"]
    earnings.sort(key=lambda x: (
        x.get("date", ""),
        0 if x.get("symbol") in priority else 1
    ))

    st.markdown("""
<div style="color:#64748b; font-size:12px; margin-bottom:16px;">
Upcoming earnings for the next 7 days. BMO = Before Market Open · AMC = After Market Close
</div>""", unsafe_allow_html=True)

    current_date = None
    for e in earnings[:50]:
        date_str = e.get("date", "")
        if date_str != current_date:
            current_date = date_str
            st.markdown(f"""
<div style="color:#4b8bf5; font-size:13px; font-weight:700;
margin:16px 0 8px 0; padding-bottom:6px; border-bottom:1px solid #1a2130;">
📅 {date_str}
</div>""", unsafe_allow_html=True)

        sym = e.get("symbol", "")
        hour = e.get("hour", "")
        timing = "🌅 BMO" if hour == "bmo" else "🌆 AMC" if hour == "amc" else "⏰ TBD"
        eps_est = e.get("epsEstimate")
        eps_act = e.get("epsActual")
        rev_est = e.get("revenueEstimate")

        eps_str = f"${eps_est:.2f}" if eps_est is not None else "N/A"
        rev_str = f"${rev_est/1e9:.2f}B" if rev_est and rev_est > 1e9 else \
                  f"${rev_est/1e6:.0f}M" if rev_est and rev_est > 1e6 else "N/A"

        if eps_act is not None:
            beat = eps_act >= eps_est if eps_est else None
            result_color = "#4ade80" if beat else "#f87171"
            result_str = f'<span style="color:{result_color}; font-weight:700;">{"BEAT" if beat else "MISS"} ${eps_act:.2f}</span>'
        else:
            result_str = '<span style="color:#64748b;">Pending</span>'

        is_priority = sym in priority
        border_color = "#4b8bf5" if is_priority else "#1a2130"

        st.markdown(f"""
<div style="background:#0d1219; border:1px solid {border_color}; border-radius:8px;
padding:12px 16px; margin-bottom:8px; display:flex; align-items:center; gap:16px;">
    <div style="min-width:70px;">
        <span style="color:#e2e8f0; font-weight:700; font-size:15px;
        font-family:JetBrains Mono,monospace;">{sym}</span>
    </div>
    <div style="color:#64748b; font-size:12px; min-width:70px;">{timing}</div>
    <div style="flex:1;">
        <span style="color:#94a3b8; font-size:12px;">EPS Est: </span>
        <span style="color:#e2e8f0; font-size:12px; font-weight:600;">{eps_str}</span>
        <span style="color:#64748b; font-size:12px; margin:0 8px;">|</span>
        <span style="color:#94a3b8; font-size:12px;">Rev Est: </span>
        <span style="color:#e2e8f0; font-size:12px; font-weight:600;">{rev_str}</span>
    </div>
    <div>{result_str}</div>
</div>""", unsafe_allow_html=True)


def render_economic_calendar():
    events = get_economic_calendar()
    if not events:
        st.info("No economic calendar data available right now.")
        return

    # Filter to high impact only first, fallback to all
    high = [e for e in events if str(e.get("impact", "")).lower() == "high"]
    display = high if high else events

    st.markdown("""
<div style="color:#64748b; font-size:12px; margin-bottom:16px;">
Key economic events for the next 14 days. High impact events highlighted in red.
</div>""", unsafe_allow_html=True)

    current_date = None
    for e in display[:40]:
        date_str = e.get("time", "")[:10] if e.get("time") else e.get("date", "")
        if date_str != current_date:
            current_date = date_str
            st.markdown(f"""
<div style="color:#4b8bf5; font-size:13px; font-weight:700;
margin:16px 0 8px 0; padding-bottom:6px; border-bottom:1px solid #1a2130;">
🗓 {date_str}
</div>""", unsafe_allow_html=True)

        impact = str(e.get("impact", "")).lower()
        impact_color = "#f87171" if impact == "high" else \
                       "#f59e0b" if impact == "medium" else "#64748b"
        impact_label = impact.upper() if impact else "LOW"

        event_name = e.get("event", e.get("name", "Unknown Event"))
        country = e.get("country", "")
        actual = e.get("actual", "")
        estimate = e.get("estimate", "")
        prev = e.get("prev", "")

        st.markdown(f"""
<div style="background:#0d1219; border:1px solid #1a2130;
border-left:3px solid {impact_color}; border-radius:8px;
padding:12px 16px; margin-bottom:8px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="color:#e2e8f0; font-weight:600; font-size:14px;">{event_name}</span>
            <span style="color:#64748b; font-size:12px; margin-left:8px;">{country}</span>
        </div>
        <span style="color:{impact_color}; font-size:11px; font-weight:700;
        background:{impact_color}22; padding:2px 8px; border-radius:4px;">{impact_label}</span>
    </div>
    <div style="margin-top:6px; display:flex; gap:16px; font-size:12px;">
        <span style="color:#94a3b8;">Actual: <span style="color:#e2e8f0;">{actual or "—"}</span></span>
        <span style="color:#94a3b8;">Estimate: <span style="color:#e2e8f0;">{estimate or "—"}</span></span>
        <span style="color:#94a3b8;">Previous: <span style="color:#e2e8f0;">{prev or "—"}</span></span>
    </div>
</div>""", unsafe_allow_html=True)


def render_sec_filings():
    filings = get_sec_filings()
    if not filings:
        st.info("No SEC filings available right now.")
        return

    st.markdown("""
<div style="color:#64748b; font-size:12px; margin-bottom:16px;">
Latest SEC filings for your watched tickers.
</div>""", unsafe_allow_html=True)

    for f in filings:
        sym = f.get("symbol", "")
        form = f.get("form", "")
        filed = f.get("filedDate", "")
        desc = f.get("description", form)
        url = f.get("reportUrl") or f.get("filingUrl") or "#"

        form_color = "#f87171" if form in ["8-K", "SC 13G", "SC 13D"] else \
                     "#4b8bf5" if form in ["10-K", "10-Q"] else "#94a3b8"

        st.markdown(f"""
<a href="{url}" target="_blank" style="text-decoration:none;">
<div style="background:#0d1219; border:1px solid #1a2130; border-radius:8px;
padding:12px 16px; margin-bottom:8px; display:flex; align-items:center;
gap:16px; transition:border-color .15s ease;"
onmouseover="this.style.borderColor='#4b8bf5'"
onmouseout="this.style.borderColor='#1a2130'">
    <span style="color:#e2e8f0; font-weight:700; font-size:14px;
    font-family:JetBrains Mono,monospace; min-width:60px;">{sym}</span>
    <span style="color:{form_color}; font-size:12px; font-weight:700;
    background:{form_color}22; padding:2px 10px; border-radius:4px;
    min-width:50px; text-align:center;">{form}</span>
    <span style="color:#94a3b8; font-size:13px; flex:1;">{desc}</span>
    <span style="color:#64748b; font-size:12px;">{filed}</span>
</div></a>""", unsafe_allow_html=True)
def render_news_page():
    st.markdown(CSS, unsafe_allow_html=True)

    left, right = st.columns([6, 1])
    with right:
        if st.button("🔄 Refresh", use_container_width=True):
            fetch_news.clear()
            get_snapshot.clear()
            st.rerun()

    feed, source = fetch_news(limit=50)
    if not feed:
        st.warning("All three news sources are currently unavailable. Try refreshing in a few minutes.")
        return
    st.caption(f"Source: {source}")

    # --- Market Snapshot Bar ---
    snapshot = get_snapshot()
    if snapshot:
        cols = st.columns(len(snapshot))
        for col, (label, (price, pct)) in zip(cols, snapshot.items()):
            color = "#4ade80" if pct >= 0 else "#f87171"
            arrow = "▲" if pct >= 0 else "▼"
            if label in ["VIX", "10Y Yield"]:
                price_str = f"{price:.2f}"
            elif price > 1000:
                price_str = f"{price:,.0f}"
            else:
                price_str = f"{price:.2f}"
            col.markdown(f"""
<div style="background:#0d1219; border:1px solid #1a2130; border-radius:10px;
padding:12px 16px; text-align:center; margin-bottom:16px;">
    <div style="color:#64748b; font-size:11px; font-weight:600;
    letter-spacing:0.5px; font-family:JetBrains Mono,monospace;">{label}</div>
    <div style="color:#e2e8f0; font-size:18px; font-weight:700;
    margin:4px 0 2px; font-family:JetBrains Mono,monospace;">{price_str}</div>
    <div style="color:{color}; font-size:12px; font-weight:700;">{arrow} {pct:+.2f}%</div>
</div>""", unsafe_allow_html=True)

    # --- Sentiment Summary ---
    labels = [a.get("overall_sentiment_label", "Neutral") for a in feed]
    bullish = sum(1 for l in labels if "Bullish" in l)
    bearish = sum(1 for l in labels if "Bearish" in l)
    total = len(labels)
    bull_pct = int((bullish / total) * 100) if total else 0
    bear_pct = int((bearish / total) * 100) if total else 0
    neu_pct = 100 - bull_pct - bear_pct

    if bull_pct > 50:
        mood, mood_color = "Bullish", "#4ade80"
    elif bear_pct > 50:
        mood, mood_color = "Bearish", "#f87171"
    elif bull_pct > bear_pct:
        mood, mood_color = "Leaning Bullish", "#86efac"
    elif bear_pct > bull_pct:
        mood, mood_color = "Leaning Bearish", "#fca5a5"
    else:
        mood, mood_color = "Neutral", "#94a3b8"

    st.markdown(f"""
<div style="background:#0d1219; border:1px solid #1a2130; border-radius:10px;
padding:14px 20px; margin-bottom:20px; display:flex; align-items:center; gap:20px;">
    <div>
        <div style="color:#64748b; font-size:11px; font-weight:600;
        letter-spacing:0.5px;">MARKET SENTIMENT</div>
        <div style="color:{mood_color}; font-size:20px; font-weight:800;
        margin-top:2px;">● {mood}</div>
    </div>
    <div style="flex:1; background:#1a2130; border-radius:999px; height:8px; overflow:hidden;">
        <div style="display:flex; height:100%;">
            <div style="width:{bull_pct}%; background:#4ade80;"></div>
            <div style="width:{neu_pct}%; background:#475569;"></div>
            <div style="width:{bear_pct}%; background:#f87171;"></div>
        </div>
    </div>
    <div style="display:flex; gap:16px; font-size:12px; font-family:JetBrains Mono,monospace;">
        <span style="color:#4ade80;">▲ {bull_pct}%</span>
        <span style="color:#94a3b8;">● {neu_pct}%</span>
        <span style="color:#f87171;">▼ {bear_pct}%</span>
    </div>
</div>""", unsafe_allow_html=True)

    # --- News Tabs ---
    tab_news, tab_earnings, tab_econ, tab_sec = st.tabs([
        "📰 Top News", "📅 Earnings", "🗓 Economic Calendar", "📄 SEC Filings"
    ])
    with tab_news:
        render_top_news(feed)
    with tab_earnings:
        render_earnings()
    with tab_econ:
        render_economic_calendar()
    with tab_sec:
        render_sec_filings()


if __name__ == "__main__":
    st.set_page_config(page_title="Market Terminal — News", layout="wide")
    st.title("📰  Market News")
    render_news_page()