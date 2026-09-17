import asyncio
import sys
try:
    from crawl4ai import AsyncWebCrawler
except ImportError:
    print("Crawl4ai not installed yet")
    sys.exit(1)

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://search.brave.com/search?q=hackathons")
        print(result.markdown[:500])

if __name__ == "__main__":
    asyncio.run(main())
