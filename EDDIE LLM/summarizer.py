# import re
# import requests
# from bs4 import BeautifulSoup
# import tiktoken
# import httpx
# import os
# from dotenv import load_dotenv

# load_dotenv()
# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# # -------------------------------
# # 1. FETCH FILING TEXT
# # -------------------------------
# def fetch_filing_text(url: str) -> str:
#     """Download HTML from SEC and clean the text."""
#     try:
#         headers = {"User-Agent": "EDDIE-Financial-Assistant/1.0"}
#         res = requests.get(url, headers=headers)
#         res.raise_for_status()
#     except Exception as e:
#         return f"[ERROR fetching filing]: {str(e)}"

#     soup = BeautifulSoup(res.text, "html.parser")

#     # Remove unnecessary HTML elements
#     for tag in soup(["script", "style", "nav", "header", "footer", "img", "table"]):
#         tag.decompose()

#     text = soup.get_text(" ")

#     # Normalize whitespace
#     clean_text = " ".join(text.split())
#     return clean_text


# # -------------------------------
# # 2. SPLIT 10-K SECTIONS
# # -------------------------------
# def split_10k_sections(text: str) -> dict:
#     pattern = r"(ITEM[\s\xa0]+[0-9]{1,2}[A]?(?:\.[\s\xa0]*[A-Z0-9 \-\&]+)?)"
#     parts = re.split(pattern, text, flags=re.IGNORECASE)

#     sections = {}
#     for i in range(1, len(parts), 2):
#         header = parts[i].replace("\xa0", " ").strip()
#         content = parts[i + 1].strip()
#         sections[header] = content

#     return sections


# # -------------------------------
# # 3. CHUNK INTO LLM-SAFE BLOCKS
# # -------------------------------
# def chunk_text(text: str, max_tokens: int = 2000, overlap_tokens: int = 200) -> list:
#     """
#     Splits large text into manageable chunks based on token count.
#     """

#     enc = tiktoken.get_encoding("cl100k_base")
#     words = text.split()
#     chunks = []
#     current_words = []

#     for word in words:
#         current_words.append(word)

#         token_count = len(enc.encode(" ".join(current_words)))

#         if token_count > max_tokens:
#             # save the chunk except overlap
#             chunk = " ".join(current_words[:-overlap_tokens])
#             chunks.append(chunk)

#             # keep overlap for next chunk
#             current_words = current_words[-overlap_tokens:]

#     # last chunk
#     if current_words:
#         chunks.append(" ".join(current_words))

#     return chunks


# # -------------------------------
# # 4. SUMMARIZE A SINGLE CHUNK
# # -------------------------------
# def summarize_chunk(chunk: str, user_query: str, model: str = "openai/gpt-oss-20b:free") -> str:
#     """Summarize one chunk with strict factual rules."""

#     prompt = f"""
# You are a strictly factual summarization model.

# User request:
# {user_query}

# Summarize ONLY this chunk:
# {chunk}

# Rules:
# - Do NOT hallucinate.
# - Summarize ONLY what is inside this chunk.
# - If the chunk contains no relevant info, return an empty string.
# """

#     try:
#         response = httpx.post(
#             "https://openrouter.ai/api/v1/chat/completions",
#             headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
#             json={
#                 "model": model,
#                 "messages": [{"role": "user", "content": prompt}],
#                 "temperature": 0.1,
#             },
#             timeout=60,
#         )
#         data = response.json()
#         return data["choices"][0]["message"]["content"].strip()
#     except Exception as e:
#         return f"[ERROR summarizing chunk]: {str(e)}"


# # -------------------------------
# # 5. MERGE CHUNK SUMMARIES
# # -------------------------------
# def merge_summaries(chunk_summaries: list, user_query: str, model: str = "openai/gpt-oss-20b:free") -> str:
#     """Merge several chunk summaries into a clean answer."""

#     # Remove empty chunks
#     summaries = [s for s in chunk_summaries if s.strip()]

#     if not summaries:
#         return "The requested information is not available in the extracted filing."

#     prompt = f"""
# Merge these chunk summaries into a clean, concise, factual summary.

# User request:
# {user_query}

# Chunk summaries:
# {summaries}

# Rules:
# - Do NOT add new information.
# - Do NOT hallucinate.
# - Summarize only what appears in the chunk summaries.
# """

#     try:
#         response = httpx.post(
#             "https://openrouter.ai/api/v1/chat/completions",
#             headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
#             json={
#                 "model": model,
#                 "messages": [{"role": "user", "content": prompt}],
#                 "temperature": 0.1,
#             },
#             timeout=60,
#         )
#         data = response.json()
#         return data["choices"][0]["message"]["content"].strip()

#     except Exception as e:
#         return f"[ERROR merging summaries]: {str(e)}"


# # -------------------------------
# # 6. MAIN PIPELINE FUNCTION
# # -------------------------------
# def process_filing_for_summary(
#     filing_url: str,
#     user_query: str,
# ) -> str:
#     """
#     Full Option D pipeline:
#     - fetch HTML
#     - extract text
#     - detect sections
#     - pick relevant sections
#     - chunk
#     - summarize
#     - merge
#     """

#     print("📥 Fetching filing text...")
#     text = fetch_filing_text(filing_url)
#     print (text)
#     print("-------------------------------")

#     print("🧩 Splitting into sections...")
#     sections = split_10k_sections(text)
#     q = user_query.lower()

#     # decide which sections to use
#     relevant_sections = []

#     if "risk" in q:
#         for key in sections:
#             if "1A" in key.upper():
#                 relevant_sections.append(sections[key])

#     elif "md&a" in q or "management" in q:
#         for key in sections:
#             if key.upper().startswith("ITEM 7"):
#                 relevant_sections.append(sections[key])

#     else:
#         # fallback: use entire filing
#         relevant_sections = list(sections.values())

#     print("🔪 Chunking sections...")
#     chunks = []
#     for sec in relevant_sections:
#         chunks.extend(chunk_text(sec))

#     print(f"📝 Summarizing {len(chunks)} chunks...")
#     chunk_summaries = []
#     for chunk in chunks:
#         chunk_summaries.append(summarize_chunk(chunk, user_query))

#     print("📚 Merging chunk summaries...")
#     final_summary = merge_summaries(chunk_summaries, user_query)
#     print("-------------------------------")
#     print(final_summary)

#     return final_summary





# summarizer.py
"""
Summarizer module for EDGAR filings (10-K / 8-K)
Flow:
1. Download filing HTML
2. Convert to TXT
3. Save -> docs/<ticker>_<year>_<form>.txt
4. Extract relevant sections based on user query
5. Chunk text into token-safe blocks
6. Summarize each chunk using openai/gpt-oss-20b:free on OpenRouter
7. Merge summaries into final answer
"""

import os
import re
import requests
import httpx
from bs4 import BeautifulSoup
import tiktoken
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTERAPIKEY")
if not OPENROUTER_API_KEY:
    raise Exception("❌ Missing OPENROUTER_APIKEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# -------------------------------------------------------
# 1. Download & clean filing HTML
# -------------------------------------------------------
def fetch_and_clean_filing(url: str) -> str:
    """Fetch HTML filing, clean extraneous tags, return pure text."""
    try:
        headers = {
    "User-Agent": "Shounak/1.0 (EDDIE; shounak@example.com)",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
    }

        res = requests.get(url, headers=headers, timeout=30)
        res.raise_for_status()
    except Exception as e:
        return f"[ERROR fetching filing: {str(e)}]"

    soup = BeautifulSoup(res.text, "html.parser")

    # Remove unnecessary HTML
    for tag in soup(["script", "style", "table", "img", "nav", "header", "footer"]):
        tag.decompose()

    text = soup.get_text(" ")
    clean_text = " ".join(text.split())  # normalize whitespace
    return clean_text


# -------------------------------------------------------
# 2. Save TXT file for local re-use
# -------------------------------------------------------
def save_txt(ticker: str, year: int, form: str, text: str) -> str:
    folder = "docs"
    os.makedirs(folder, exist_ok=True)

    filename = f"{ticker}_{year}_{form}.txt"
    filepath = os.path.join(folder, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    return filepath


# -------------------------------------------------------
# 3. Detect relevant sections in a 10-K
# -------------------------------------------------------
def extract_relevant_sections(text: str, user_query: str) -> list:
    """
    Identify sections based on keywords in user query.
    Default → use full text.
    """

    sections = []

    # Section splits: ITEM 1., ITEM 1A., ITEM 7., ITEM 8.
    pattern = r"(ITEM\s+\d+[A]?(?:\.\s*[A-Z0-9 \-&]+)?)"
    parts = re.split(pattern, text, flags=re.IGNORECASE)

    section_map = {}
    for i in range(1, len(parts), 2):
        section_map[parts[i].upper()] = parts[i + 1]

    q = user_query.lower()

    if "risk" in q:
        for key, content in section_map.items():
            if "1A" in key:
                sections.append(content)

    elif "md&a" in q or "management discussion" in q or "item 7" in q:
        for key, content in section_map.items():
            if key.startswith("ITEM 7"):
                sections.append(content)

    elif "financial statements" in q or "item 8" in q:
        for key, content in section_map.items():
            if key.startswith("ITEM 8"):
                sections.append(content)

    else:
        # Default: use entire filing text
        sections = [text]

    return sections


# -------------------------------------------------------
# 4. Chunk large text into token-safe blocks
# -------------------------------------------------------
def chunk_text(text: str, max_tokens: int = 2000, overlap_tokens: int = 200) -> list:
    enc = tiktoken.get_encoding("cl100k_base")
    words = text.split()
    chunks, current = [], []

    for word in words:
        current.append(word)
        if len(enc.encode(" ".join(current))) > max_tokens:
            chunks.append(" ".join(current[:-overlap_tokens]))
            current = current[-overlap_tokens:]

    if current:
        chunks.append(" ".join(current))

    return chunks


# -------------------------------------------------------
# 5. Summarize a single chunk using openai/gpt-oss-20b:free
# -------------------------------------------------------
def summarize_chunk(chunk: str, user_query: str) -> str:
    prompt = f"""
You are a strictly factual summarizer.

User request:
{user_query}

Summarize ONLY the following chunk:
{chunk}

Rules:
- No hallucination.
- Only summarize content from the chunk.
- If irrelevant, return an empty string.
"""

    try:
        res = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "openai/gpt-oss-20b:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=60,
        )

        data = res.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"[ERROR chunk summary: {str(e)}]"


# -------------------------------------------------------
# 6. Merge multiple chunk summaries
# -------------------------------------------------------
def merge_summaries(chunk_summaries: list, user_query: str) -> str:
    summaries = [s for s in chunk_summaries if s.strip()]

    if not summaries:
        return "The requested information is not available in the extracted filing."

    prompt = f"""
Merge the following chunk summaries into a single, clear, factual summary.

User request:
{user_query}

Chunk summaries:
{summaries}

Rules:
- No hallucination.
- Do NOT add new information.
- Use only what appears in the chunk summaries.
"""

    try:
        res = httpx.post(
            OPENROUTER_URL,
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "openai/gpt-oss-20b:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=60,
        )

        data = res.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        return f"[ERROR merging: {str(e)}]"


# -------------------------------------------------------
# 7. MAIN FUNCTION CALLED EXTERNALLY
# -------------------------------------------------------
def get_filing_summary(user_query: str, filing_url: str) -> str:
    """
    Main entry point used in llm_pipeline
    """
    print("📥 Downloading filing...")
    print(filing_url)
    text = fetch_and_clean_filing(filing_url)

    # Extract ticker/year/form from URL if possible original
    # match = re.search(r"data/(\d+)/(\d{4})(\d{2})(\d{2})", filing_url)
    # ticker = "UNKNOWN"
    # print(match)
    # year = 0
    # form = "10-K"


    # cik_match = re.search(r"data/(\d+)/", filing_url)
    # if cik_match:
    #     cik = cik_match.group(1)
    # else:
    #     cik = "UNKNOWN"

    # # ------------------------------------------
    # # 2. Extract filing date → year
    # # ------------------------------------------
    # # Matches patterns like aapl-20240928.htm or amzn-20231231.htm
    # date_match = re.search(r"(\d{8})\.htm", filing_url)
    
    # if date_match:
    #     date_str = date_match.group(1)
    #     filing_year = int(date_str[:4])
    # else:
    #     filing_year = None

    # # ------------------------------------------
    # # 3. Form type (must come from dispatch ideally)
    # # ------------------------------------------
    # form_type = fallback_form

    

    # if match:
    #     year = int(match.group(2))
    # ticker must come from dispatch; we extract it upstream

    # ------------------------------------------
    # 2. Save TXT locally





# OLD WRONG CODE HERE — REPLACE IT
# match = re.search(...)
# ticker = ...
# year = ...
# form = ...

# NEW INLINE CODE:
    cik_match = re.search(r"data/(\d+)/", filing_url)
    if cik_match:
        cik = cik_match.group(1)
    else:
        cik = "UNKNOWN"

    date_match = re.search(r"(\d{8})\.htm", filing_url)
    if date_match:
        filing_date = date_match.group(1)
        year = int(filing_date[:4])
    else:
        year = None

    # Determine form type; fallback to 10-K if not available
    form_type = "10-K"

#---------------------------------------------------------------
    # Save cleaned text
    save_txt(cik, year, form_type, text)

    print("🔍 Extracting relevant sections...")
    sections = extract_relevant_sections(text, user_query)

    print("✂️ Chunking...")
    chunks = []
    for sec in sections:
        chunks.extend(chunk_text(sec))

    print(f"📝 Summarizing {len(chunks)} chunks...")
    chunk_summaries = [summarize_chunk(c, user_query) for c in chunks]

    print("📚 Merging summaries...")
    final_summary = merge_summaries(chunk_summaries, user_query)

    return final_summary
