from ddgs import DDGS
from database import save_opportunity

def search_and_store_opportunities(query="latest software engineering internships hackathons students"):
    print(f"Scraping DuckDuckGo for: {query}...")
    
    count = 0
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if tavily_key:
        print(f"Scraping Tavily API for: {query}...")
        try:
            import requests
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": tavily_key, "query": query, "search_depth": "basic", "max_results": 10}
            )
            if resp.status_code == 200:
                tavily_data = resp.json()
                for r in tavily_data.get("results", []):
                    title = r.get('title', 'Unknown')
                    link = r.get('url', '')
                    desc = r.get('content', '')
                    save_opportunity(title, "Tavily", link, desc)
                    count += 1
        except Exception as e:
            print(f"Tavily search failed: {e}")

    # Fallback to DuckDuckGo to augment results
    if count == 0:
        print(f"Scraping DuckDuckGo for: {query}...")
        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=10)
            
            if results:
                for r in results:
                    title = r.get('title', 'Unknown')
                    link = r.get('href', '')
                    desc = r.get('body', '')
                    source = "DuckDuckGo"
                    save_opportunity(title, source, link, desc)
                    count += 1
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}. (Anti-bot protection active?)")
            
    print(f"Saved {count} real opportunities to database.")
    return count
