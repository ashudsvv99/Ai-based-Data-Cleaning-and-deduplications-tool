# `backend/domain_profiler.py` - Industry Context Detector

A "Price" column in a Retail dataset means something very different than a "Price" column in a Real Estate dataset. To make smart decisions, the AI needs to know what industry the data belongs to. The `DomainProfiler` class handles this using a robust **Two-Pass Detection System**.

## Full Working Process & Logic

### 1. `DOMAIN_KEYWORDS` Dictionary
At the top of the file, there is a hardcoded dictionary mapping Domains to Keywords (e.g., `"Retail": ["customer", "order", "delivery"]`). This acts as an ultra-fast, local heuristic pre-filter. Instead of immediately paying API costs to guess the domain, we check this dictionary first.

### 2. Pass 1: Keyword Scoring (`_keyword_score()`)
This method runs instantly using pure Pandas. 
- **Column Name Matching**: It iterates through `df.columns`, lowercases them, and checks if any substrings match the `DOMAIN_KEYWORDS`. If it finds `"order"`, the `"Retail"` score gets `+1`.
- **Sample Value Matching**: It doesn't just look at headers! It takes the top 20 non-null values of every string column (`df[col].dropna().astype(str).str.lower().head(20).tolist()`) and scans them. If a value contains a keyword, it adds `+0.5` to that domain's score.
- It returns the domain with the highest score as the `heuristic_result`.

### 3. Pass 2: LLM Verification (`_llm_detect()`)
Heuristics aren't perfect. What if the dataset is from the "Legal" industry (which isn't in our dictionary)?
- We build a compact sample by taking `df.head(3)` and converting it to a JSON dictionary.
- We construct a `system_prompt` strictly enforcing a JSON output structure using Pydantic-like instructions (`{"domain": "...", "confidence": "..."}`).
- We pass the `heuristic_result` to the LLM as a *hint*. The LLM is instructed: "Here is what the heuristic guessed. Look at the column names and sample rows. Either confirm the guess, or override it if you detect a domain the keyword list doesn't cover."
- It calls `self.llm_client.chat_completion_json()` which forces the LLM response into a Python dictionary.

### Error Handling & Fallbacks
If the LLM times out, crashes, or returns malformed JSON, the `try-except` block in `detect_domain()` catches the `Exception` and gracefully falls back to returning the Pass 1 `heuristic_result`. This guarantees the pipeline never crashes just because the AI had a hiccup!
