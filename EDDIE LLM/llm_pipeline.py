# llm_pipeline.py
"""
LLM pipeline that:
1. Converts natural language queries into JSON for FastAPI dispatch
2. Sends the JSON to /dispatch
3. Summarizes the dispatch output using OpenRouter LLMs
"""
import sys
from pathlib import Path

# Get path to "work/" directory
WORK_DIR = Path(__file__).resolve().parent.parent

# Add it to sys.path if not already there
if str(WORK_DIR) not in sys.path:
    sys.path.insert(0, str(WORK_DIR))

# sys.path.append("RAG")   # to import from parent dir
from RAG.rag_engine import ingest_filing,rag_pipeline
from rich.console import Console
# import google.generativeai as genai
import os
import json
import requests
import re
from dotenv import load_dotenv
#from summarizer import get_filing_summary
load_dotenv()
console = Console()
# -----------------------------------------
# CONFIG
# -----------------------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise Exception("❌ Missing OPENROUTER_API_KEY environment variable")

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# if not GEMINI_API_KEY:
#     console.print("[bold red]CRITICAL: GEMINI_API_KEY not found in .env[/bold red]")
#     exit()

# We use 1.5 Flash because it is the most stable free-tier model currently
# genai.configure(api_key=GEMINI_API_KEY)
# MODEL = genai.GenerativeModel("gemini-2.5-flash-lite")

LLM_URL = os.getenv("LLM_URL")
DISPATCH_URL = "http://localhost:8000/dispatch"   # FastAPI service
# DISPATCH_URL = "https://eddie-backend-production.up.railway.app/dispatch" 

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}
#Prompt modifications required heavily based on the model used. The current prompt is optimized for openrouter models.

# -----------------------------------------
# 1) LLM converts natural language → JSON
# -----------------------------------------

def llm_generate_json(user_query: str) -> dict:
    """
    Convert natural language query → JSON for /dispatch.
    """

    prompt = prompt = f"""
You are an EDGAR Dispatch JSON Converter.

Your job is to convert ANY user query into a STRICT JSON request for the FastAPI EDGAR Dispatch API.

---------------------------------------
JSON Fields Specification
---------------------------------------
JSON MUST include:

1. ticker  
   - Always uppercase  
   - If the user gives a CIK instead of ticker, place "" for ticker and include "cik".  
     Example: "cik": "0001018724"

2. actions  
   - A list of valid actions from:  
        - get_cik  
        - get_company_info  
        - get_company_submissions  
        - get_company_facts  
        - get_filings_10k_8k

3. form_type  
   - Required only when user explicitly asks for 10-K or 8-K  
   - Allowed values: "10-K", "8-K"

4. year (optional)

5. quarter (optional)

6. metrics (optional) — used only for filtering facts

7. cik (optional) — only when user gives a CIK instead of a stock ticker.

---------------------------------------
Rules
---------------------------------------
- Output STRICT JSON. No explanation. No extra text.
- Use previous conversation context when interpreting incomplete queries.
- Deduce the correct actions from the user query:
    • “CIK of Tesla” → ["get_cik"]  
    • “Company info for MSFT” → ["get_company_info"]  
    • “Give me 2023 10-K for AAPL” → ["get_filings_10k_8k"]  
    • “Fetch revenue of AMZN for 2022” → ["get_company_facts"]

- If user gives a CIK directly, skip resolving ticker.

---------------------------------------
Example
---------------------------------------
User: "Get Apple's 2024 10-K"
Output:
{{
    "ticker": "AAPL",
    "actions": ["get_filings_10k_8k"],
    "form_type": "10-K",
    "year": 2024
}}

---------------------------------------
Now convert the following user request:
"{user_query}"
"""


    payload = {
        "model": "openai/gpt-oss-120b:free",        # or "deepseek/deepseek-chat", "google/gemini-2.0-pro-exp"
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 500
    }
    print(payload)
    response = requests.post(LLM_URL, headers=HEADERS, json=payload)
    # print("[yellow]3. Asking Gemini to convert query to JSON...[/yellow]")
    # print(prompt)
    # print("-----------------")
    # response = MODEL.generate_content(prompt)
    print("LLM Response:")
    print(response)
    data = response.json()
    print(data)
    print("-----------------")

    raw_output = data["choices"][0]["message"]["content"]

    # Extract strict JSON
    match = re.search(r"\{.*\}", raw_output, re.S)
    if not match:
        raise Exception(f"❌ Invalid JSON from LLM: {raw_output}")

    json_query = json.loads(match.group(0))
    return json_query



# -----------------------------------------
# 2) Send JSON → FastAPI dispatch
# -----------------------------------------

def call_dispatch(json_payload: dict) -> dict:
    """
    Sends the JSON payload to FastAPI /dispatch.
    """

    response = requests.post(DISPATCH_URL, json=json_payload)

    if response.status_code != 200:
        raise Exception(f"❌ Dispatch API failed: {response.text}")

    return response.json()



# -----------------------------------------
# 3) LLM summarizes dispatch output
# -----------------------------------------

# def llm_summarize(dispatch_output: dict, user_query: str) -> str:
#     """
#     Summarize the dispatch response into readable text.
#     """

#     prompt = f"""
# You are a strictly factual financial analysis model. 
# Your job is to read:
# 1. The user's request
# 2. The EDGAR Dispatch API JSON output

# Then produce ONLY the information that directly answers the user's request.
# Do NOT add ANY extra details that are not explicitly present in the JSON or in the provided 10-K/8-K URLs.

# ---------------------------------------
# STRICT RULES (MUST FOLLOW)
# ---------------------------------------
# • ONLY use the data present inside the dispatch JSON.
# • If the user refers to a topic inside a 10-K or 8-K, you MUST read the provided filing URL from the dispatch JSON and summarize ONLY the relevant section.
# • NEVER invent financial numbers, trends, risks, or insights.
# • NEVER add assumptions about the company unless explicitly given in the JSON.
# • If the requested information is missing, respond EXACTLY with:
#   "The requested information is not available in the retrieved EDGAR data."
# > Refer the urls in the dispatch JSON for 10-K/8-K filings when request is about those filings and must.
# (Note : Use the URLs to get the relevant information from the filings, do not just mention the URLs in the answer.)

# ---------------------------------------
# ANSWERING LOGIC
# ---------------------------------------
# 1. Identify exactly what the user wants.
# 2. Look for the requested information in the dispatch JSON.
# 3. If found → summarize it clearly and concisely.
# 4. If not found → state that it is not available.
# 5. DO NOT include anything extra.
# 6. DO NOT generalize.
# 7. DO NOT hallucinate.
# 8. DO NOT expand into unrelated analysis.
# 9. DO NOT include the full JSON or raw numeric dumps.

# ---------------------------------------
# AVAILABLE DATA (JSON from dispatch)
# ---------------------------------------
# {json.dumps(dispatch_output, indent=2)}

# ---------------------------------------
# NOW FINAL TASK
# ---------------------------------------
# Based on ONLY the above JSON and the user request:
# • Answer the user's question precisely
# • Use no additional information
# • Be concise and strictly factual
# • Use 10-K or 8-K URLs ONLY whenever the user specifically asks about content from those filings.

# User Request:
# \"\"\"{user_query}\"\"\"
# """


#     payload = {
#         "model": "openai/gpt-oss-20b:free",     # default summarizer
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": 0.5,
#         "max_tokens": 1500
#     }

#     response = requests.post(LLM_URL, headers=HEADERS, json=payload)
#     data = response.json()
#     print(data)
#     print("-----------------")

#     if "error" in data:
#         raise Exception(f"❌ LLM Error: {data['error']}")

#     if "choices" not in data:
#         raise Exception(f"❌ Unexpected LLM response: {data}")

#     final_answer = data["choices"][0]["message"]["content"]

#     return final_answer
from test import test_extract_filing_url

def llm_summarize(
    dispatch_output: dict,
    user_query: str,
    year: int | None = None,
    ticker: str | None = None
) -> str:
    ...

    """
    Summarize the dispatch response into readable text.
    """

    # ----------------------------------------------------
    # 🔥 NEW: Detect if user wants FILING TEXT (10-K / 8-K)
    # ----------------------------------------------------
    user_lower = user_query.lower()
    print(user_lower)

    wants_filing_text = any(keyword in user_lower for keyword in [
        "10-k", "10k",
        "8-k", "8k",
        "risk", "risk factors",
        "md&a", "management discussion",
        "liquidity", "operations",
        "business overview", "filing text", "full report"
    ])

    if wants_filing_text:
        try:
            # filings = dispatch_output.get("filings", [])
            # print(filings)

            # filing_url = test_extract_filing_url(filings)
            # print(filing_url)
            print("-----------------")
            print("this is the dispatch output",dispatch_output)
            print("🔍 User requests detailed filing text. Extracting filing URL...")
            filing_url = test_extract_filing_url(dispatch_output)
            print("Filing URL extracted for detailed summary:", filing_url)
            print("Ingesting filing URL:", filing_url)
            print(ticker, year, filing_url)
            print("Ingesting filing...")
            ingest_filing(ticker, year, filing_url)

            return rag_pipeline(user_query, ticker, year)

            #return get_filing_summary(user_query, filing_url) # Get detailed summary from filing URL replace the previous function call with rag ??

        except Exception as e:
            return f"[ERROR processing filing text]: {str(e)}"

    # ----------------------------------------------------
    # ❗ DEFAULT: Your OLD JSON-only summarizer (unchanged)
    # ----------------------------------------------------

    prompt = f"""
You are a strictly factual financial analysis model. 
Your job is to read:
1. The user's request
2. The EDGAR Dispatch API JSON output

Then produce ONLY the information that directly answers the user's request.
Do NOT add ANY extra details that are not explicitly present in the JSON or in the provided 10-K/8-K URLs.

STRICT RULES:
• ONLY use the data inside the dispatch JSON.
• If the user refers to a topic inside a 10-K or 8-K, you MUST read the provided URL and summarize ONLY the relevant section.
• NEVER hallucinate.
• If data is missing → respond EXACTLY:
  "The requested information is not available in the retrieved EDGAR data."

Dispatch JSON:
{json.dumps(dispatch_output, indent=2)}

User Request:
\"\"\"{user_query}\"\"\" 
"""

    payload = {
        "model": "openai/gpt-oss-120b:free",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 1500
    }

    response = requests.post(LLM_URL, headers=HEADERS, json=payload)
    # response = MODEL.generate_content(prompt)
    data = response.json()
    print(data)

    if "error" in data:
        raise Exception(f"❌ LLM Error: {data['error']}")

    if "choices" not in data:
        raise Exception(f"❌ Unexpected LLM response: {data}")

    final_answer = data["choices"][0]["message"]["content"]

    return final_answer



# -----------------------------------------
# 4) MAIN PIPELINE FUNCTION
# -----------------------------------------

def process_user_query(user_query: str) -> str:
    """
    Entire pipeline:
        → user text
        → LLM JSON conversion
        → dispatch call
        → LLM summarization
        → final natural language answer
    """

    print("🔍 Step 1 → Converting query to JSON...")
    print(user_query)
    print("---------------------")
    json_query = llm_generate_json(user_query)
    print(f"Generated JSON:{json_query}")
    report = json_query
    year = report.get("year") # Extract year and ticker for later use this is the latest change
    if year is None:
        year = None
    ticker = report.get("ticker")# Extract year and ticker for later use this is the latest change
    if ticker is None:
        ticker = None

    print(f"Generated JSON: {json.dumps(json_query, indent=2)}")
    print("---------------------")

    print("📡 Step 2 → Sending JSON to /dispatch...")
    dispatch_result = call_dispatch(json_query)
    print(dispatch_result)
    print("---------------------")

    print("🧠 Step 3 → Summarizing dispatch output...")
    summary = llm_summarize(dispatch_result, user_query, year, ticker)
    print(summary)
    print("---------------------")
    print("✅ Pipeline complete.")
    print("-------------------------------------------------------------------")

    return summary



# -----------------------------------------
# Local test (optional)
# -----------------------------------------

# if __name__ == "__main__":
#     query = "Get me the 2024 10-K report for Apple and summarize it."
#     print(process_user_query(query))
