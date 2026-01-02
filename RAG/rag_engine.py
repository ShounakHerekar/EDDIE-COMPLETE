"""
Eddie RAG Engine - Free Tier Optimized
--------------------------------------
1. Embeddings: Local (HuggingFace via ChromaDB) -> unlimited, free.
2. Summary: Gemini 1.5 Flash -> Fast, single API call.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console

# Load environment variables
load_dotenv()
console = Console()

# ------------------------------------------------------
# CONFIG
# ------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    console.print("[bold red]CRITICAL: GEMINI_API_KEY not found in .env[/bold red]")
    exit()

# We use 1.5 Flash because it is the most stable free-tier model currently
genai.configure(api_key=GEMINI_API_KEY)
MODEL = genai.GenerativeModel("gemini-2.5-flash-lite")

CHROMA_DB_DIR = "./chroma_db_local"

# ------------------------------------------------------
# 1. SETUP DATABASE (LOCAL EMBEDDINGS)
# ------------------------------------------------------

# This downloads a small, free model (all-MiniLM-L6-v2) to your machine.
# No API keys required for this part!
local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

collection = chroma_client.get_or_create_collection(
    name="filings_local",
    metadata={"hnsw:space": "cosine"},
    embedding_function=local_ef  # <--- WE USE LOCAL FUNCTION NOW
)

# ------------------------------------------------------
# 2. FETCH & CLEAN
# ------------------------------------------------------

def fetch_html(url: str) -> str:
    try:
        headers = {
            "User-Agent": "EddieTest/2.0 (student_project@example.com)",
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        time.sleep(0.2) 
        return r.text
    except Exception as e:
        console.print(f"[red]Fetch Error:[/red] {e}")
        return ""

def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "xbrl", "header", "footer"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    return "\n".join([t.strip() for t in text.splitlines() if t.strip()])

# ------------------------------------------------------
# 3. CHUNK & INGEST (NO API LIMITS!)
# ------------------------------------------------------

def chunk_text_simple(text: str, chunk_size=1000, overlap=200):
    """Simple character-based chunking to avoid token API limits."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += (chunk_size - overlap)
    return chunks

def ingest_filing(company: str, year: str, url: str):
    console.print(f"[yellow]1. Fetching {company} 10-K...[/yellow]")
    html = fetch_html(url)
    if not html: return

    console.print("[yellow]2. Cleaning text...[/yellow]")
    text = clean_html(html)

    # Simple split by "Item" to get context headers (Rough heuristic)
    # We treat the whole text as a stream for simplicity in this robust version
    chunks = chunk_text_simple(text)
    
    console.print(f"[yellow]3. Embedding {len(chunks)} chunks locally... (This uses CPU, not API)[/yellow]")
    
    # Clean old data
    collection.delete(where={"$and": [{"company": company}, {"year": year}]})

    # Batch process to be safe
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        ids = [f"{company}_{year}_{i+j}" for j in range(len(batch))]
        metas = [{"company": company, "year": year} for _ in batch]
        
        # .add() automatically calls the local embedding model
        collection.add(
            ids=ids,
            documents=batch,
            metadatas=metas
        )
        print(f".", end="", flush=True)

    console.print(f"\n[green]✔ Successfully indexed {company}.[/green]")

# ------------------------------------------------------
# 4. SEARCH & ANSWER
# ------------------------------------------------------

def rag_pipeline(query: str, company: str, year: str):
    # 1. RETRIEVE (Local - Fast)
    if len(query.strip()) > 10:
        k=6           #for longer queries, get more context
    else:
        k=2
    console.print(f"[yellow]3. Retrieving top {k} chunks from local DB...[/yellow]")
    results = collection.query(
        query_texts=[query], # Chroma embeds this query locally for us!
        n_results=k,
        where={"$and": [{"company": company}, {"year": year}]}
    )

    if not results["documents"][0]:
        return "No data found."

    # 2. GENERATE (Gemini - 1 Call Only)
    context_text = "\n---\n".join(results["documents"][0])
    
    prompt = f"""
You are a financial analyst.
Answer STRICTLY using the context below.
Be concise. Use Paragraphs. Bullet points where appropriate.

QUESTION:
{query}

CONTEXT:
{context_text}
"""


    try:
        console.print("[yellow]4. Asking Gemini (1 API Call)...[/yellow]")
        response = MODEL.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini Error: {e}"

# ------------------------------------------------------
# 5. TEST EXECUTION
# ------------------------------------------------------

# if __name__ == "__main__":
#     console.rule("[bold cyan]EDDIE RAG - FREE TIER MODE[/bold cyan]")
    
#     # TEST CASE: MICROSOFT 2023 10-K
#     COMPANY = "TSLA"
#     YEAR = "2023"
#     URL = "https://www.sec.gov/Archives/edgar/data/1065280/000106528023000035/nflx-20221231.htm"
    
#     # 1. Run Ingestion (Local Embeddings)
#     ingest_filing(COMPANY, YEAR, URL)
    
#     # 2. Run Query
#     QUERY = """Netflix’s 2022 Form 10-K states that it is involved in multiple ongoing legal proceedings, including copyright, patent, employment, tax, and securities class actions, but does not quantify potential losses or name specific cases.

# Explain why U.S. securities law permits this level of disclosure, and analyze under what exact conditions Netflix would be legally required to (a) disclose specific litigation details or (b) recognize a litigation-related liability in its financial statements.

# In your answer, reference the interaction between SEC disclosure requirements, materiality thresholds, and accounting treatment under U.S. GAAP.* """

#     answer = rag_pipeline(QUERY, COMPANY, YEAR)
    
#     console.rule("[bold green]ANSWER[/bold green]")
#     console.print(answer)