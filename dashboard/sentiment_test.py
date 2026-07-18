#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 14 21:46:56 2026

@author: daniel
"""

import os
from dotenv import load_dotenv
import requests

load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))
api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

if not api_key:
    print("ERROR: API key not found. Check your .env file.")
else:
    print(f"API key Loaded successfully (starts with: {api_key[:4]}. . .)")
    
    
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": "AAPL",
        "apikey": api_key,
        "limit": 5
    }
    
    
    response = requests.get(url, params=params)
    data = response.json()
    
    
    print("Top-level keys in response:", list(data.keys()))
    print()

    if "feed" in data:
        print(f"Success! Retrieved {len(data['feed'])} news articles.\n")
        for article in data["feed"][:3]:
            print(f"- {article['title']}")
            print(f"  Sentiment: {article['overall_sentiment_label']} ({article['overall_sentiment_score']})\n")
    else:
        print("Unexpected response:")
        print(data)