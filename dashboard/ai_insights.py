#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 15 13:12:26 2026

@author: daniel
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv
import requests
import streamlit as st
from google import genai

# --- Setup ---
load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

st.set_page_config(page_title="Market Terminal", layout="wide", page_icon="📈")

# --- Custom styling ---
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stButton>button {
        background-color: #1f2937;
        color: white;
        border: 1px solid #374151;
    }
    .headline-card {
        background-color: #161b22;
        border-left: 3px solid #374151;
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .bullish { border-left-color: #22c55e !important; }
    .bearish { border-left-color: #ef4444 !important; }
    .neutral { border-left-color: #6b7280 !important; }
    .ticker-badge {
        display: inline-block;
        background-color: #1f2937;
        color: #9ca3af;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar controls ---
st.sidebar.title("⚙️ Controls")
tickers = st.sidebar.text_input("Tickers", "AAPL,MSFT,NVDA")
limit = st.sidebar.slider("Articles", 5, 50, 20)
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=False)
refresh_interval = st.sidebar.slider("Refresh interval (sec)", 30, 300, 60, disabled=not auto_refresh)
manual_fetch = st.sidebar.button("🔄 Fetch Now", use_container_width=True)

st.sidebar.divider()
st.sidebar.caption(f"Last updated: {st.session_state.get('last_update', 'Never')}")

# --- Header ---
col_title, col_status = st.columns([4, 1])
with col_title:
    st.title("📈 Market Terminal")
with col_status:
    st.write("")
    if auto_refresh:
        st.success("🟢 Live", icon="✅")

def sentiment_class(label):
    if "Bullish" in label:
        return "bullish"
    elif "Bearish" in label:
        return "bearish"
    return "neutral"

def sentiment_icon(label):
    if "Bullish" in label:
        return "🟢"
    elif "Bearish" in label:
        return "🔴"
    return "⚪"

def fetch_and_render():
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": tickers,
        "apikey": av_key,
        "limit": limit
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "feed" not in data:
        st.error(f"Failed to retrieve news: {data}")
        return

    articles = data["feed"]
    st.session_state["last_update"] = datetime.now().strftime("%H:%M:%S")

    # Summary metrics
    bullish_count = sum(1 for a in articles if "Bullish" in a["overall_sentiment_label"])
    bearish_count = sum(1 for a in articles if "Bearish" in a["overall_sentiment_label"])
    neutral_count = len(articles) - bullish_count - bearish_count

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Articles", len(articles))
    m2.metric("🟢 Bullish", bullish_count)
    m3.metric("🔴 Bearish", bearish_count)
    m4.metric("⚪ Neutral", neutral_count)

    st.divider()

    # AI Insights
    with st.spinner("Generating AI insights..."):
        headline_block = ""
        for a in articles:
            headline_block += f"- {a['title']} (sentiment: {a['overall_sentiment_label']})\n"

        client = genai.Client(api_key=gemini_key)
        prompt = f"""You are a financial market analyst. Below is a list of recent news headlines
with their sentiment labels, covering {tickers}.

Summarize the key market-moving themes in 4-6 concise bullet points, grouped by ticker
where relevant. Note any notable sentiment shifts or risks. Be factual and concise,
no speculation beyond what the headlines support.

Headlines:
{headline_block}
"""
        result = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt
        )

    st.subheader("🤖 AI Insights")
    st.info(result.text)

    st.divider()

    # Headlines
    st.subheader("📰 Headlines")
    for a in articles:
        cls = sentiment_class(a["overall_sentiment_label"])
        icon = sentiment_icon(a["overall_sentiment_label"])
        tickers_in_article = ", ".join(
            t["ticker"] for t in a.get("ticker_sentiment", [])[:4]
        )
        st.markdown(f"""
        <div class="headline-card {cls}">
            <div style="font-size:15px; font-weight:600; color:#e5e7eb;">{icon} {a['title']}</div>
            <div style="margin-top:4px;">
                <span class="ticker-badge">{a['source']}</span>
                <span class="ticker-badge">{tickers_in_article}</span>
                <span class="ticker-badge">{a['overall_sentiment_label']} ({a['overall_sentiment_score']})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- Run logic ---
placeholder = st.empty()

if manual_fetch or auto_refresh:
    with placeholder.container():
        fetch_and_render()
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
else:
    st.info("Click **'Fetch Now'** or enable **Auto-refresh** in the sidebar to begin.")