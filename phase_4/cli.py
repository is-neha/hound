import argparse
from database import init_db, get_all_opportunities
from scraper import search_and_store_opportunities
from llm import query_llm
from tts import speak

def main():
    parser = argparse.ArgumentParser(description="Hound - Phase 4 CLI")
    parser.add_argument("command", choices=["scrape", "prompt", "allwork", "listen", "wake"], help="Command to run")
    parser.add_argument("query", nargs="?", default="", help="Query for scraping or prompt")
    parser.add_argument("--mute", action="store_true", help="Mute audio")
    
    args = parser.parse_args()
    
    # Initialize SQLite database
    init_db()
    
    if args.command == "scrape":
        q = args.query if args.query else "software engineering internship student"
        search_and_store_opportunities(q)
    elif args.command == "allwork":
        ops = get_all_opportunities()
        summary = f"You have {len(ops)} tracked opportunities. "
        for o in ops:
            summary += f"{o['title']}, "
        print(f"\n[Hound]: {summary}")
        audio_process = speak(summary, args.mute)
        if audio_process:
            audio_process.join()
    elif args.command == "listen":
        from listen import start_voice_loop
        start_voice_loop()
    elif args.command == "wake":
        from wake import run_wake_word_engine
        run_wake_word_engine()
    elif args.command == "prompt":
        if not args.query:
            print("Please provide a prompt. Example: python cli.py prompt \"What internships do I have?\"")
            return
            
        if "set reminder for" in args.query.lower() or "set a reminder for" in args.query.lower():
            import re
            import threading
            match = re.search(r'(\d+)\s*(minute|min|second|sec|hour|hr)', args.query.lower())
            if match:
                val = int(match.group(1))
                unit = match.group(2)
                secs = val
                if 'min' in unit: secs = val * 60
                elif 'hour' in unit or 'hr' in unit: secs = val * 3600
                
                def timer_done():
                    print(f"\n\n[Hound]: 🚨 BEEP! Your {val} {unit} reminder is up! 🚨")
                    p = speak(f"[URGENT] Reminder! Your {val} {unit} timer is up!", args.mute)
                    if p: p.join()
                    
                threading.Timer(secs, timer_done).start()
                answer = f"Timer set for {val} {unit}."
                print(f"[Hound]: {answer}")
                p = speak(answer, args.mute)
                if p: p.join()
                return

        print("Thinking...")
        answer = query_llm(args.query)
        print(f"\n[Hound]: {answer}")
        
        # Audio output of the LLM response
        p = speak(answer, args.mute)
        if p: p.join()

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
