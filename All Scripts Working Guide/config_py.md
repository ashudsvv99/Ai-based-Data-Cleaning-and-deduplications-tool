# `config.py` - The Global Configuration & Hyperparameters

In enterprise software engineering, you never hardcode variables (like API URLs or mathematical thresholds) directly into operational scripts. If a threshold needs to change, hunting through 25 files to find it is dangerous. `config.py` acts as the single source of truth for all global hyperparameters.

## Full Working Process & Logic

### 1. Data Cleaning Markers (`MISSING_VALUE_MARKERS`)
- **Logic**: We define a master list of strings: `["Unknown", "-", "None", "NaN", "<Na>", "N/A", "null", ""]`.
- **Why**: Different industries denote missing data differently. A retail app might use `N/A`, while a database export might use `NULL`. By centralizing this list here, `loader.py` can import it and run a global `.replace()` to force all these rogue strings into standardized `pd.NA` objects for the statistical engines to handle properly.

### 2. Algorithmic Thresholds
- **`FUZZY_MATCH_THRESHOLD = 85`**: Imported by `deduplication.py`. It tells the RapidFuzz Levenshtein algorithm exactly how strict it needs to be. 85 means strings must be 85% mathematically similar to be merged.
- **`IQR_MULTIPLIER = 1.5`**: Imported by `outliers.py`. This is the standard statistical multiplier used to calculate the Interquartile Range bounds. 1.5 is standard, but if we wanted extreme outlier clipping, we could lower it to 1.2 here.

### 3. API Resilience Rules
- **`MAX_RETRIES = 3`**: Local LLMs (via LM Studio) are prone to timeouts if the GPU runs out of VRAM. This integer controls the exponential backoff loop in `llm_client.py`.
- **`LLM_API_BASE = "http://localhost:1234/v1"`**: The standard port for LM Studio. If we ever swap to Ollama (port 11434) or vLLM (port 8000), we only change this one line, and all 5 AI Agents instantly adapt.
