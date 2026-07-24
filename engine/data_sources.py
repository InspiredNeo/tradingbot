import os 
import time
from dotenv import load_dotenv
import requests
from google import genai


load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))

gemini_key = os.getenv("GEMINI_API_KEY")
_gemini_client = genai.Client(api_key=gemini_key)


ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
TWELVE_DATA_KEY = os.getenv("TWELVE_DATA_API_KEY")

#Tracks which sources are temporarily marked as down, and when they were marked
_source_status ={
    "alpha_vantage": {"down": False, "down_since": 0},
    "finnhub": {"down": False, "down_since": 0},
    "twelve_data": {"down": False, "down_since": 0},
}


# How long to wait before retrying a source that failed (in seconds)
COOLDOWN_SECONDS = 3600


def _mark_down(source_name):
    _source_status[source_name]["down"] = True
    _source_status[source_name]["down_since"] = time.time()
    
    
    
def _is_available(source_name):
    status = _source_status[source_name]
    if not status["down"]:
        return True
    # Check if cooldown period has passed
    if time.time() - status["down_since"] > COOLDOWN_SECONDS:
        status["down"] = False
        return True
    return False


def _fetch_alpha_vantage(tickers, limit):
    if not _is_available("alpha_vantage"):
        return None
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": tickers,
            "apikey": ALPHA_VANTAGE_KEY,
            "limit": limit
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        
        if "feed" not in data or len(data.get("feed", [])) == 0:
            _mark_down("alpha_vantage")
            return None
        
        
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
        articles = []
        for a in data["feed"]:
            # Find the sentiment for the most relevant requested ticker
            best_label = a.get("overall_sentiment_label", "Neutral")
            best_score = a.get("overall_sentiment_score", 0)
            best_relevance = -1
            for ts in a.get("ticker_sentiment", []):
                if ts["ticker"].upper() in ticker_list:
                    rel = float(ts.get("relevance_score", 0))
                    if rel > best_relevance:
                        best_relevance = rel
                        best_label = ts.get("ticker_sentiment_label", best_label)
                        best_score = ts.get("ticker_sentiment_score", best_score)
            articles.append({
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("source", "Alpha Vantage"),
                "summary": a.get("summary", ""),
                "banner_image": a.get("banner_image", ""),
                "sentiment_label": best_label,
                "sentiment_score": best_score,
                "tickers": [t["ticker"] for t in sorted(a.get("ticker_sentiment", []), key=lambda x: float(x.get("relevance_score", 0)), reverse=True)[:4]],
                "data_source": "Alpha Vantage"
            })
        return articles
    except Exception:
        _mark_down("alpha_vantage")
        return None
    
    
def _fetch_finnhub(tickers,limit):
    if not _is_available("finnhub"):
        return None
    try:
        import finnhub
        finnhub_client = finnhub.Client(api_key=FINNHUB_KEY)
        
        
        symbol_list = tickers.split(",")
        articles = []
        for symbol in symbol_list:
            news = finnhub_client.company_news(
            symbol.strip(),
            _from="2026-01-01",
            to="2026-12-31"
        )
        for item in news[:limit]:
            articles.append({
                "title": item.get("headline", ""),
                "url": item.get("url", ""),
                "source": item.get("source", "Finnhub"),
                "summary": item.get("summary", ""),
                "banner_image": item.get("image", ""),
                "sentiment_label": "Neutral",
                "sentiment_score": 0,
                "tickers": [symbol.strip()],
                "data_source": "Finnhub"
            })
            
            
        if len(articles) == 0:
            _mark_down("finnhub")
            return None
        return _score_sentiment(articles[:limit])
    except Exception:
        _mark_down("finnhub")
        return None
    
    
    
    
def _fetch_twelve_data(tickers, limit):
    if not _is_available("twelve_data"):
        return None
    try:
        import requests
        
        
        symbol_list = tickers.split(",")
        articles =[]
        
        
        for symbol in symbol_list:
            url = "https:api.twelvedata.com/news"
            params = {
                "symbol": symbol.strip(),
                "apikey": TWELVE_DATA_KEY,
                "outputsize": limit
            }
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            
            if "data" not in data:
                continue
            
            
            for item in data["data"]:
                articles.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", "Twelve Data"),
                    "summary": item.get("content", "")[:300],
                    "banner_image": item.get("image_url", ""),
                    "sentiment_label": "Neutral",
                    "sentiment_score": 0,
                    "tickers": [symbol.strip()],
                    "data_source": "Twelve Data"
                })
                
                
        if len(articles) == 0:
            _mark_down("twelve_data")
            return None
        return _score_sentiment(articles[:limit])
    except Exception:
        _mark_down("twelve_data")
        return None
                
                
            
                    
    
def _score_sentiment(articles):
    try:
        titles = [a["title"] for a in articles]
        numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
        prompt = (
            "You are a financial sentiment analyst. For each headline below, "
            "respond with ONLY the number and one of these exact labels: "
            "Bullish, Somewhat-Bullish, Neutral, Somewhat-Bearish, Bearish.\n"
            "One per line, no explanation, no punctuation after the label.\n\n"
            f"{numbered}"
        )
        result = _gemini_client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt
        )
        lines = result.text.strip().split("\n")
        for i, line in enumerate(lines):
            if i >= len(articles):
                break
            parts = line.strip().split(" ", 1)
            label = parts[-1].strip() if len(parts) > 1 else "Neutral"
            if label in ["Bullish", "Somewhat-Bullish", "Neutral", "Somewhat-Bearish", "Bearish"]:
                articles[i]["sentiment_label"] = label
                score_map = {
                    "Bullish": 0.5,
                    "Somewhat-Bullish": 0.25,
                    "Neutral": 0.0,
                    "Somewhat-Bearish": -0.25,
                    "Bearish": -0.5,
                }
                articles[i]["sentiment_score"] = score_map.get(label, 0.0)
    except Exception:
        pass
    return articles

    

def _deduplicate(articles):
    seen_titles = set()
    unique_articles = []
    for a in articles:
        normalized_title = a["title"].strip().lower()
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_articles.append(a)
    return unique_articles



def get_news(tickers, limit=20):
    """
    Main entry point. Tries each source in order untill one succeeds.
    Returns a deduplicated ;ist of articles, or and empty list if all sources fail.
    """
    result = _fetch_alpha_vantage(tickers,limit)
    if result:
        return _deduplicate(result)
    
    
    result = _fetch_finnhub(tickers, limit)
    if result:
        return _deduplicate(result)
    
    
    result = _fetch_twelve_data(tickers, limit)
    if result:
        return _deduplicate(result)
    
    
    return []

