import time
import json
import random
import hashlib
import os
import datetime
import requests
from dotenv import load_dotenv
from openai import OpenAI
from ddgs import DDGS
from database import init_db, insert_opportunity

load_dotenv("../phase_5/.env") # Load existing env

# We need the user's primary API key for background structuring.
def get_api_key():
    try:
        with open("../phase_5/api_keys.json", "r") as f:
            keys = json.load(f)
            return keys.get("gemini", [])[0]
    except Exception:
        return None

def read_profile():
    try:
        with open("profile.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

def generate_search_queries(profile, focus):
    print(f"[Daemon] Generating unique search queries for focus: {focus}...")
    client = OpenAI(
        api_key=get_api_key(), 
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    prompt = f"""
    Today's date is {datetime.date.today().isoformat()}.
    Based on this user profile: {json.dumps(profile)}
    Generate exactly 3 diverse, specific DuckDuckGo search queries focusing on: {focus}.
    Ensure they are different from generic searches to find fresh, currently active results.
    Return ONLY a JSON list of 3 strings. Example: ["query 1", "query 2", "query 3"]
    """
    
    try:
        resp = client.chat.completions.create(
            model="gemini-3.6-flash",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        # Parse the JSON array
        content = resp.choices[0].message.content
        import re
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return [f"{profile.get('education', 'Student')} {focus} 2026"]
    except Exception as e:
        print(f"[Daemon] LLM Query Generation failed: {e}")
        return [f"{focus} opportunities 2026"]

def process_and_store_results(query, results):
    if not results: return
    
    print(f"[Daemon] Structuring {len(results)} results for query: '{query}'...")
    client = OpenAI(
        api_key=get_api_key(), 
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    # Force the LLM to output a precise JSON schema
    schema_prompt = f"""
    Today's date is {datetime.date.today().isoformat()}.
    Analyze these raw web search results. If they are error pages, captchas, or irrelevant, return {{"opportunities": []}}.
    Otherwise, extract valid opportunities and return a JSON object with this exact structure:
    {{
        "opportunities": [
            {{
                "title": "Exact Title",
                "link": "URL",
                "spoken_alert": "A brief, 1-sentence conversational alert. (e.g. 'Hey, the XYZ hackathon deadline is approaching.')",
                "urgency_score": 1 to 10 (10 if deadline is within 7 days),
                "is_deadline": true or false,
                "expiration_date": "YYYY-MM-DD" (guess the date if missing, or add 30 days)
            }}
        ]
    }}
    """
    
    try:
        resp = client.chat.completions.create(
            model="gemini-3.6-flash",
            messages=[
                {"role": "system", "content": schema_prompt},
                {"role": "user", "content": json.dumps(results)}
            ],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(resp.choices[0].message.content)
        opps = data.get("opportunities", [])
        
        for opp in opps:
            opp_id = hashlib.md5((opp['title'] + opp['link']).encode()).hexdigest()
            insert_opportunity(
                opp_id, opp['title'], opp['link'], opp['spoken_alert'],
                opp['urgency_score'], opp['is_deadline'], opp['expiration_date'], query
            )
            print(f"  -> Saved: {opp['title']} (Urgency: {opp['urgency_score']})")
            
    except Exception as e:
        print(f"[Daemon] LLM Processing failed: {e}")

def run_daemon_cycle():
    topics = ["Internships", "Hackathons", "Tech News", "Scholarships", "Open Source"]
    
    while True:
        try:
            print(f"\n[{datetime.datetime.now()}] Waking up for research cycle...")
            profile = read_profile()
            
            # 1. Pick a random focus to avoid search stagnation
            focus = random.choice(topics)
            
            # 2. Generate novel queries
            queries = generate_search_queries(profile, focus)
            
            # 3. Search and Process
            ddgs = DDGS()
            for q in queries:
                print(f"[Daemon] Searching DDG: '{q}'...")
                # Add random sleep to prevent DDG IP Ban
                time.sleep(random.uniform(2, 5)) 
                try:
                    results = list(ddgs.text(q, max_results=3, backend="lite"))
                    
                    enriched_results = []
                    for res in results:
                        link = res.get('href')
                        if link:
                            print(f"    [Jina] Reading full page: {link}...")
                            try:
                                jina_resp = requests.get(f"https://r.jina.ai/{link}", timeout=15)
                                if jina_resp.status_code == 200:
                                    res['body'] = jina_resp.text[:10000] # Cap text to avoid massive token blows
                            except Exception as ex:
                                print(f"    [Jina] Failed to scrape {link}: {ex}")
                        enriched_results.append(res)
                        time.sleep(1) # Prevent hammering Jina

                    process_and_store_results(q, enriched_results)
                except Exception as e:
                    print(f"[Daemon] Search failed for '{q}': {e}")
                    
            # 4. Sleep with Jitter (45 to 75 minutes)
            sleep_time = random.uniform(2700, 4500)
            print(f"[{datetime.datetime.now()}] Cycle complete. Sleeping for {int(sleep_time/60)} minutes...")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"[Daemon] CRITICAL ERROR in main loop: {e}. Recovering in 1 hour...")
            time.sleep(3600)

if __name__ == "__main__":
    init_db()
    print("=========================================")
    print(" HOUND DAEMON: Autonomous Research Agent ")
    print("=========================================")
    run_daemon_cycle()
