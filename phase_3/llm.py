import os
from openai import OpenAI
from dotenv import load_dotenv
from database import get_all_opportunities
from duckduckgo_search import DDGS

load_dotenv()

# We expect the user to configure these in a .env file
API_KEY = os.getenv("API_KEY", "your-api-key-here")
BASE_URL = os.getenv("BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("MODEL", "gpt-3.5-turbo")

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL
)

def query_llm(user_prompt):
    # 1. Load local data
    local_data = get_all_opportunities()
    context = f"Local Database Records:\n{local_data}\n\n"
    
    # 2. Construct system prompt
    system_prompt = (
        "You are Hound, an autonomous AI scout for a programmer. "
        "Use the provided Local Database Records to answer the user's questions about internships and hackathons. "
        "If the answer is NOT in the database, explicitly say 'I need to search the web for that'."
    )
    
    try:
        # 3. Call LLM
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt + context},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        answer = response.choices[0].message.content
        
        # 4. Fallback logic: If LLM needs to search
        if "I need to search the web" in answer:
            print("[Hound]: Missing data locally. Falling back to live web search...")
            ddgs = DDGS()
            results = ddgs.text(user_prompt, max_results=3)
            
            fallback_prompt = (
                f"Here are live web search results for the user's query:\n{results}\n\n"
                f"Please synthesize a helpful answer for the user."
            )
            
            fallback_response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are Hound. Answer based on the provided web search results."},
                    {"role": "user", "content": fallback_prompt}
                ]
            )
            return fallback_response.choices[0].message.content

        return answer
    except Exception as e:
        return f"Error communicating with LLM: {e}\nPlease check your .env file."
