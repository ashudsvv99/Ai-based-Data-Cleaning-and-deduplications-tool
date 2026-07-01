# `cleaning/multilingual.py` - The Scalable Translation Engine

In a global dataset, a user might enter their city as "München" or "म्यूनिख" instead of "Munich". If you don't translate these to a standard language (English), the Deduplication engine will fail to recognize them as duplicates, and categorizations will be fractured. 

The `MultilingualEngine` class translates the dataset, but does so with extreme Token caching to avoid crashing the LLM.

## Full Working Process & Logic

### 1. ASCII Pre-Filter
- **Logic**: Calling an LLM costs money and time. If a column is already fully English, we shouldn't translate it.
- **Action**: The engine iterates through categorical/string columns and runs a fast Python string check to see if all characters are valid ASCII. If yes, it completely skips the column.

### 2. The $O(1)$ Token Caching Strategy
- **Problem**: If the dataset has 50,000 rows, and 10,000 of them say "दिल्ली" (Delhi), sending 10,000 individual translation requests to the LLM would take 3 hours and cost a fortune in API tokens.
- **Action**: 
  1. The script extracts only the unique strings from the column: `unique_vals = df[col].dropna().unique()`.
  2. It filters these unique values down to ONLY the non-ASCII ones.
  3. It builds a JSON payload and sends *only* this unique list to the LLM (e.g., `["दिल्ली", "München"]`). 
  4. The LLM translates them and returns a JSON mapping: `{"दिल्ली": "Delhi", "München": "Munich"}`.
  5. The script applies this tiny dictionary across all 50,000 rows instantly using Pandas vectorization: `df[col] = df[col].replace(translation_map)`.
- **Result**: We translated 50,000 rows using a single API call containing just a few words.

### 3. Fallbacks
If the LLM fails to translate a weird unicode character, the engine falls back to the Python `unidecode` library. `unidecode` performs raw phonetic transliteration (turning Unicode bytes into closest-matching ASCII chars). It's not semantically perfect (e.g., it might just strip accents), but it guarantees the data becomes ASCII-safe for the deduplication engine.
