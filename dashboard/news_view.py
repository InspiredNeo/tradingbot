"""
news_view.py — CNN-style news page for the Market Terminal
"""

import os
import html
from datetime import datetime, timezone

import requests
import streamlit as st
from dotenv import load_dotenv

# --- Config ---
load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

AV_URL = "https://www.alphavantage.co/query"
CACHE_TTL_SECONDS = 1800  # 30 minutes

SENTIMENT_COLORS = {
    "Bullish": "#12b76a",
    "Somewhat-Bullish": "#4caf50",
    "Neutral": "#8a8f98",
    "Somewhat-Bearish": "#f59e0b",
    "Bearish": "#ef4444",
}


# --- Data ---
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


def _fetch_alpha_vantage(limit):
    """Try Alpha Vantage NEWS_SENTIMENT. Returns (feed_list, error_or_None)."""
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
        if "feed" in data:
            return data["feed"], None
        msg = (data.get("Information") or data.get("Note")
               or data.get("Error Message") or "No feed returned.")
        return [], msg
    except Exception as exc:
        return [], str(exc)


def _fetch_finnhub(limit):
    """Try Finnhub general market news. Returns (feed_list, error_or_None)."""
    if not FINNHUB_API_KEY:
        return [], "No Finnhub key."
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": FINNHUB_API_KEY},
            timeout=15,
        )
        raw = resp.json()
        if not isinstance(raw, list) or len(raw) == 0:
            return [], "Finnhub returned no articles."
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
        return feed, None
    except Exception as exc:
        return [], str(exc)


def _fetch_twelve_data(limit):
    """Try Twelve Data news endpoint. Returns (feed_list, error_or_None)."""
    if not TWELVE_DATA_API_KEY:
        return [], "No Twelve Data key."
    try:
        resp = requests.get(
            "https://api.twelvedata.com/news",
            params={"apikey": TWELVE_DATA_API_KEY, "count": limit},
            timeout=15,
        )
        data = resp.json()
        raw = data.get("data") or data.get("news") or []
        if not raw:
            return [], "Twelve Data returned no articles."
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
        return feed, None
    except Exception as exc:
        return [], str(exc)


def _finnhub_time(unix_ts):
    """Convert Finnhub unix timestamp to Alpha Vantage format YYYYMMDDTHHMMSS."""
    try:
        return datetime.utcfromtimestamp(int(unix_ts)).strftime("%Y%m%dT%H%M%S")
    except Exception:
        return ""


def _twelve_time(iso_str):
    """Convert Twelve Data ISO string to Alpha Vantage format YYYYMMDDTHHMMSS."""
    try:
        dt = datetime.strptime(iso_str[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y%m%dT%H%M%S")
    except Exception:
        return ""


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_news(tickers="", topics="", limit=50):
    """Try Alpha Vantage → Finnhub → Twelve Data. Returns (feed, source_name)."""
    feed, err = _fetch_alpha_vantage(limit)
    if feed:
        return feed, "Alpha Vantage"

    feed, err = _fetch_finnhub(limit)
    if feed:
        return feed, "Finnhub"

    feed, err = _fetch_twelve_data(limit)
    if feed:
        return feed, "Twelve Data"

    return [], None


# --- Helpers ---
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
.hero img { width: 100%; height: 400px; object-fit: cover; display: block; }
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
  display: block; background: #1a2332; border: 1px solid #2d3748; border-radius: 12px; overflow: hidden;
  box-shadow: 0 2px 10px rgba(0,0,0,.12); transition: transform .12s ease, box-shadow .12s ease;
}
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 22px rgba(0,0,0,.20); }
.card img { width: 100%; height: 168px; object-fit: cover; display: block; }
.card-body { padding: 14px 15px 16px; }
.card-body h3 { color: #e5e7eb; font-size: 16px; line-height: 1.3; margin: 9px 0 6px; font-weight: 700; }
.card-body p  { color#9aa4b2; font-size: 13px; line-height: 1.45; margin: 0; }
.breaking-list { display: flex; flex-direction: column; gap: 2px; }
.row {
  display: flex; gap: 15px; padding: 14px 8px; border-bottom: 1px solid rgba(128,128,128,.22);
  align-items: center; transition: background .12s ease;
}
.row:hover { background: rgba(128,128,128,.08); }
.row img, .row .noimg {
  width: 132px; height: 84px; object-fit: cover; border-radius: 8px; flex: 0 0 auto;
  background: linear-gradient(135deg,#374151,#111827);
}
.row-body { flex: 1 1 auto; min-width: 0; }
.row-top { font-size: 12.5px; color: #6b7280; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.row-title { font-size: 16.5px; font-weight: 700; line-height: 1.3; margin-top: 5px; }
.live {
  color: #fff; background: #e11d2e; font-size: 11px; font-weight: 800; letter-spacing: .4px;
  padding: 2px 8px; border-radius: 4px; text-transform: uppercase;
  animation: pulse 1.6s infinite;
}
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .55; } }
.ago { font-weight: 700; color: #e11d2e; }
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
    with_img = [a for a in feed if a.get("banner_image")]
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


def render_breaking(feed):
    recent = feed[:14]
    if not recent:
        st.info("No recent headlines available right now.")
        return
    rows = ""
    for i, a in enumerate(recent):
        img = a.get("banner_image") or ""
        thumb = f'<img src="{img}">' if img else '<div class="noimg"></div>'
        flag = '<span class="live">&#9679; Live</span>' if i == 0 else ""
        rows += (
            f'<a class="row" href="{a.get("url", "#")}" target="_blank">{thumb}'
            f'<div class="row-body"><div class="row-top">{flag}'
            f'<span class="ago">{_time_ago(a.get("time_published", ""))}</span> &middot; '
            f'<span>{html.escape(a.get("source", ""))}</span> {_pill(a)}</div>'
            f'<div class="row-title">{_clean(a.get("title"), 170)}</div>'
            f'</div></a>'
        )
    st.markdown(f'<div class="news-wrap"><div class="breaking-list">{rows}</div></div>', unsafe_allow_html=True)


def render_news_page():
    st.markdown(CSS, unsafe_allow_html=True)

    left, right = st.columns([6, 1])
    with right:
        if st.button("🔄 Refresh", use_container_width=True):
            fetch_news.clear()
            st.rerun()

    feed, source = fetch_news(limit=50)
    if not feed:
        st.warning("All three news sources are currently unavailable. Try refreshing in a few minutes.")
        return
    st.caption(f"Source: {source}")

    tab_top, tab_breaking = st.tabs(["📰  Top News", "🔴  Breaking News"])
    with tab_top:
        render_top_news(feed)
    with tab_breaking:
        render_breaking(feed)


if __name__ == "__main__":
    st.set_page_config(page_title="Market Terminal — News", layout="wide")
    st.title("📰  Market News")
    render_news_page()

