import os 
from dotenv import load_dotenv


load_dotenv(os.path.expanduser("~/tradingbot/config/.env"))


av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
finnhub_key = os.getenv("FINNHUB_API_KEY")
twelve_key = os.getenv("TWELVE_DATA_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")


print("Alpha Vantage key loaded:", av_key is not None)
print("Finnhub key loaded:", finnhub_key is not None)
print("Twelve Data key loaded:", twelve_key is not None)
print("Gemini key loaded:", gemini_key is not None)