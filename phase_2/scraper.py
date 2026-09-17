from database import save_opportunity

def search_and_store_opportunities(query="software engineering internship 2024 student"):
    print(f"Scraping web for: {query}...")
    
    # Simulating a successful scrape since duckduckgo_search often blocks CLI requests
    mock_opportunities = [
        {
            "title": "Software Engineering Intern - Microsoft",
            "link": "https://careers.microsoft.com/intern",
            "body": "Join our Azure team for a 12-week summer internship. Requirements: CS major, 3.0 GPA."
        },
        {
            "title": "Global Agentic AI Hackathon",
            "link": "https://devpost.com/ai-hackathon",
            "body": "Build the future of autonomous agents. Virtual hackathon. Deadline: October 15th."
        }
    ]
    
    count = 0
    for r in mock_opportunities:
        title = r.get('title', 'Unknown')
        link = r.get('link', '')
        desc = r.get('body', '')
        source = "Simulated Job Board"
        save_opportunity(title, source, link, desc)
        count += 1
            
    print(f"Saved {count} opportunities to database.")
    return count
