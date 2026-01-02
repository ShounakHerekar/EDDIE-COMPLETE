from llm_pipeline import process_user_query

def is_greeting(text: str) -> bool:
    greetings = ["hi", "hello", "hey", "who are you", "what is eddie"]
    return any(g in text.lower() for g in greetings)

def intro():
    return """
Hi, I'm Eddie 👋 

I analyze SEC EDGAR filings (10-K, 8-K).
I use retrieval-based analysis — no guessing, no hallucination.


Try:
- "Summarize Tesla’s 2023 10-K risk factors"
- "What macroeconomic risks did Amazon report in 2022?"
"""

def main():
    print("-----------------------------------------------------")
    print(intro())
    print("EDDIE v1.0 — EDGAR Research Assistant")
    print("Type 'exit' to quit.\n")
    print("-----------------------------------------------------")
    

    while True:
        user_input = input("> ").strip()
        if user_input.lower() in ["exit", "quit", "goodbye","bye","see you","stop","end","close","terminate","finish"]:
            print("Goodbye 👋")
            break

        if is_greeting(user_input):
            print("-------------------------------------------------------------------")
            print(intro())
            print("-------------------------------------------------------------------")
        else:
            try:
                answer = process_user_query(user_input)
                print("\n" + answer + "\n")
                print("-------------------------------------------------------------------")
            except Exception as e:
                print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
