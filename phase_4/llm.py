import os
import json
from openai import OpenAI
from database import get_all_opportunities
from ddgs import DDGS

# Define the models we want to iterate through for each provider
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it"
]

OPENROUTER_MODELS = [
    "anthropic/claude-3-haiku",
    "openrouter/free",
    "nvidia/nemotron-3.5-lightning:free"
]

# Google AI Studio now has native OpenAI SDK compatibility!
GEMINI_MODELS = [
    
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite"
]
def load_rotation_pool():
    keys_file = "api_keys.json"
    if not os.path.exists(keys_file):
        raise FileNotFoundError(f"Missing {keys_file}! Please create it with your API keys.")
        
    with open(keys_file, "r") as f:
        keys = json.load(f)
        
    pool = []
    
    # 1. Load Gemini Keys & Models (PRIMARY DEFAULT)
    for key in keys.get("gemini", []):
        for model in GEMINI_MODELS:
            pool.append({
                "provider": f"Gemini ({model})",
                "api_key": key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "model": model
            })
            
    # 2. Load Groq Keys & Models (FALLBACK)
    for key in keys.get("groq", []):
        for model in GROQ_MODELS:
            pool.append({
                "provider": f"Groq ({model})",
                "api_key": key,
                "base_url": "https://api.groq.com/openai/v1",
                "model": model
            })
            
    # 3. Load OpenRouter Keys & Models (LAST RESORT)
    for key in keys.get("openrouter", []):
        for model in OPENROUTER_MODELS:
            pool.append({
                "provider": f"OpenRouter ({model})",
                "api_key": key,
                "base_url": "https://openrouter.ai/api/v1",
                "model": model
            })
            
    return pool

def _get_llm_response(messages):
    pool = load_rotation_pool()
    last_error = None
    
    for config in pool:
        print(f"[Hound]: Routing query to {config['provider']}...")
        try:
            client = OpenAI(api_key=config["api_key"], base_url=config["base_url"])
            response = client.chat.completions.create(
                model=config["model"], 
                messages=messages
            )
            return response
        except Exception as e:
            err_msg = str(e).lower()
            # Catch Rate Limits, Quota Exhaustion, Decommissioned Models, or Missing Models
            if any(error_code in err_msg for error_code in ["429", "404", "400", "insufficient_quota", "credit_balance", "rate limit", "rate_limit_exceeded", "not found", "decommissioned"]):
                print(f"[Hound]: ⚠️ {config['provider']} failed (Quota/Decommissioned). Rotating to next configuration...")
                last_error = e
                continue
            else:
                # If it's a completely different error (e.g., no internet), raise it
                raise e
                
    raise Exception(f"CRITICAL: Exhausted the entire key and model pool! Last error: {last_error}")

def query_llm(user_prompt):
    local_data = get_all_opportunities()
    
    # Load User Profile
    user_profile = ""
    try:
        with open("profile.json", "r") as f:
            user_profile = f.read()
    except Exception:
        user_profile = "Generic Student"
        
    context = f"User Profile:\n{user_profile}\n\nLocal Database Records:\n{local_data}\n\n"
    
    system_prompt = (
        "You are Hound, a highly personalized autonomous AI scout. "
        "Use the provided User Profile to deeply customize your advice. "
        "Use the provided Local Database Records to answer questions about tasks, internships, and scholarships. "
        "CRITICAL: You MUST pay attention to deadlines! If an opportunity has a deadline coming up within the next 7 days, "
        "you MUST start your response with the exact tag '[URGENT]'. "
        "If the answer is NOT in the database, explicitly say 'I need to search the web for that'."
    )
    
    messages = [
        {"role": "system", "content": system_prompt + context},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = _get_llm_response(messages)
        answer = response.choices[0].message.content
        
        # Auto-Search Fallback
        if "I need to search the web" in answer:
            print("[Hound]: Missing data locally. Falling back to live web search...")
            results = ""
            
            # 1. Try Tavily
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                try:
                    import requests
                    resp = requests.post(
                        "https://api.tavily.com/search",
                        json={"api_key": tavily_key, "query": user_prompt, "search_depth": "basic", "max_results": 3}
                    )
                    if resp.status_code == 200:
                        tavily_data = resp.json()
                        results = str(tavily_data.get("results", []))
                except Exception as e:
                    print(f"[Hound]: Tavily search failed ({e}).")

            # 2. Fallback to DuckDuckGo if Tavily fails or is missing
            if not results:
                try:
                    ddgs = DDGS()
                    results = str(ddgs.text(user_prompt, max_results=3))
                except Exception as e:
                    results = f"Web search failed: {e}"
            
            fallback_prompt = (
                f"Here are live web search results for the user's query:\n{results}\n\n"
                f"Please synthesize a helpful answer for the user."
            )
            fallback_msgs = [
                {"role": "system", "content": "You are Hound. Answer based on the provided web search results."},
                {"role": "user", "content": fallback_prompt}
            ]
            
            fallback_response = _get_llm_response(fallback_msgs)
            return fallback_response.choices[0].message.content

        return answer
    except Exception as e:
        return f"Error communicating with LLM: {e}"
