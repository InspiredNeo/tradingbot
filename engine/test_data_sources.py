from data_sources import get_news


articles = get_news("AAPL,MSFT,NVDA", limit=10)


print(f"Retrieved {len(articles)} articles\n")
for a in articles[:5]:
    print(f"- [{a['data_source']}] {a['title']}")