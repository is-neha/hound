import argparse
from database import init_db
from scraper import search_and_store_opportunities
from llm import query_llm

def main():
    parser = argparse.ArgumentParser(description="Hound - Phase 1 CLI")
    parser.add_argument("command", choices=["scrape", "prompt"], help="Command to run")
    parser.add_argument("query", nargs="?", default="", help="Query for scraping or prompt")
    parser.add_argument("--mute", action="store_true", help="Mute audio (placeholder for future phases)")
    
    args = parser.parse_args()
    
    # Initialize SQLite database
    init_db()
    
    if args.command == "scrape":
        q = args.query if args.query else "software engineering internship student"
        search_and_store_opportunities(q)
    elif args.command == "prompt":
        if not args.query:
            print("Please provide a prompt. Example: python cli.py prompt \"What internships do I have?\"")
            return
            
        print("Thinking...")
        answer = query_llm(args.query)
        print(f"\n[Hound]: {answer}")

if __name__ == "__main__":
    main()
