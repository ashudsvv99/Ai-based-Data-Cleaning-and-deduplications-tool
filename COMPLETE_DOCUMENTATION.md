# IntelliClean AI: Complete Project Documentation

## Problem Statement
In enterprise environments, raw datasets generated from diverse sources (CRMs, web scraping, legacy databases) are universally plagued with inconsistencies that traditional data cleaning scripts cannot handle. The core challenges this framework aims to solve include:

1. **Complex Deduplication**: Datasets contain Exact duplicates, Partial duplicates (differing in few fields), Fuzzy duplicates (typos like `Sameep` vs `Samip`), Semantic duplicates (`IBM` vs `International Business Machines`), and Cross-Language duplicates (`समीप` vs `Sameep`). Standard algorithms fail to resolve these dynamically.
2. **Entity vs. Free Text Handling**: Blind translation destroys critical data. We need a system that knows *never* to translate Entities (Names, Addresses, IDs) and instead transliterates them, while selectively translating Free Text (Reviews, Comments).
3. **Missing Value Intelligence**: Standard scripts fill missing numeric values with 0 and strings with "Unknown". We need intelligent imputation (Median for numerics, Mode for categorical, and strict placeholders for entity fields).
4. **Canonical Record Generation**: When duplicates are found, merging them into a single, highly-complete "Golden Record" without losing secondary data is incredibly difficult.
5. **Lack of Explainability**: Automated cleaning is often a "black box". Businesses need to know the original value, transformed value, reason for change, and confidence score for every modification.
6. **Hardware & Privacy Constraints**: Enterprise datasets are massive (up to 200MB). Running $O(N^2)$ cross-joins for fuzzy matching will crash a standard consumer machine (e.g., Intel i3 Processor, 12GB RAM). Furthermore, sending sensitive business data to external APIs (like OpenAI) violates strict privacy regulations. The solution must run entirely offline, utilizing PyArrow for memory management and highly quantized local LLMs for AI inference without CPU timeouts.

## Features and Functionalities
- **100% Local AI Integration**: Operates completely offline using Local LLMs (via LM Studio), guaranteeing zero data leakage.
- **Dynamic Multi-Agent System**: Specialized AI agents evaluate schemas, guess business domains, and generate dynamic "IF-THEN" rules to impute missing data intelligently instead of blinding filling with `0`.
- **Multilingual Translation Engine**: Automatically detects non-ASCII strings (e.g., Hindi, Spanish) and batch-translates them to standardized English to preserve deduplication integrity.
- **O(N) Semantic Deduplication**: Replaces exponential cross-join comparisons with Sorted Neighbourhood Indexing and RapidFuzz, resolving duplicates across millions of rows in seconds.
- **Intelligent Outlier Handling**: Utilizes IQR bounding and Winsorization (clipping) to normalize numerical anomalies without dropping valuable rows.
- **Real-Time Streaming UI**: Built with Streamlit, the frontend intercepts backend Python logs and AI "thoughts," streaming them directly to the user to eliminate the "black box" effect.

## Technology Stack
- **Core Language**: Python 3.10+
- **Frontend / Orchestration**: `streamlit` (for real-time UI rendering and state management).
- **Data Engineering**: 
  - `pandas`: Primary DataFrame manipulation.
  - `pyarrow`: C++ backend engine for multi-threaded, high-speed CSV/Excel ingestion.
  - `numpy`: Statistical calculations (Skewness, IQR boundaries).
- **Matching & Deduplication**:
  - `recordlinkage`: Generates O(N) sliding windows (Sorted Neighbourhood Indexing).
  - `rapidfuzz`: C++ optimized string similarity scoring (Levenshtein distance).
- **String Processing**:
  - `unidecode`: Phonetic ASCII transliteration fallback.
  - `re`: Native Python Regular Expressions for currency and syntax cleaning.
- **AI & Networking**:
  - `requests`: Used to hit the local `localhost:1234/v1` LM Studio REST API endpoint.
  - `pydantic`: For enforcing strict JSON schemas on AI outputs (if applicable).

## Installation Guide
1. **Prerequisites**: Ensure Python 3.10+ is installed on your machine.
2. **Clone the Repository**: Navigate to the project directory.
3. **Install Dependencies**:
   ```bash
   pip install streamlit pandas numpy rapidfuzz recordlinkage unidecode pyarrow requests openpyxl
   ```
4. **Set Up Local AI**: 
   - Download and install **LM Studio**.
   - Download a lightweight Instruct model (e.g., Qwen, DeepSeek-R1, or Llama 3 8B) in GGUF format (Q4_K_M recommended for 12GB RAM).
   - Start the Local Inference Server in LM Studio (Default: `http://localhost:1234/v1`).

## Usage Guide
1. Open a terminal in the root directory.
2. Run the application:
   ```bash
   streamlit run app.py
   ```
3. A browser window will open. Drag and drop your dirty `.csv` or `.xlsx` file into the upload zone.
4. Watch the "Pipeline Logs" expander as the AI streams its thought process in real-time.
5. Once complete, navigate the **Data Quality**, **Imputations**, and **Audit Trail** tabs to review the AI's decisions.
6. Click the Download button to export the fully cleaned CSV and the Markdown Summary Report.

## Project Structure
```text
IntelliClean/
├── app.py                     # Main Streamlit Frontend
├── config.py                  # Global hyperparameters and API endpoints
├── requirements.txt           # Dependency list
├── ARCHITECTURE.md            # System architecture mapping
├── DEVELOPMENT_GUIDE.md       # Optimization & scaling guide
├── All Scripts Working Guide/ # Deep-dive documentation for every .py file
├── agents/                    # The AI Cognitive Engine
│   ├── llm_client.py          # Unified LM Studio HTTP interface
│   ├── schema_agent.py        # Semantic column profiling
│   ├── planner_agent.py       # Imputation rule generation
│   ├── validation_agent.py    # Post-clean logic auditing
│   └── explanation_agent.py   # Human-readable markdown generation
├── backend/                   # Infrastructure & Orchestration
│   ├── pipeline.py            # Central 12-phase orchestrator
│   ├── loader.py              # PyArrow ingestion & missing value coercion
│   ├── domain_profiler.py     # Industry context detection
│   ├── profiler.py            # Baseline statistical calculation
│   ├── validator.py           # Hardcoded math/constraint checks
│   └── exporter.py            # File I/O for reports and CSVs
└── cleaning/                  # The Core Algorithms
    ├── quality_filter.py      # >90% sparsity & dummy data dropping
    ├── multilingual.py        # O(1) Token Caching translation
    ├── currency_converter.py  # Regex symbol extraction & INR mapping
    ├── standardizer.py        # Semantic formatting (lowercase emails, etc)
    ├── string_cleaner.py      # Zero-width char & whitespace removal
    ├── deduplication.py       # Sorted Neighbourhood fuzzy matching
    ├── entity_resolution.py   # Cluster merging and primary row backfilling
    ├── missing_values.py      # AI rule evaluation + Skewness statistical fills
    └── outliers.py            # IQR calculation and Winsorization (Clipping)
```

## Complete Workflow Architecture
1. **Ingestion & Profiling**: `loader.py` reads data via PyArrow and coerces known missing markers to `pd.NA`. `profiler.py` establishes a baseline Quality Score.
2. **Schema & Domain AI**: `SchemaAgent` categorizes columns (e.g., Email, Date, Currency). `DomainProfiler` detects the industry (e.g., Healthcare).
3. **Aggressive Scrubbing**: `QualityFilter` drops useless columns (>90% missing) and rows missing multiple critical identifiers (Phone/Email).
4. **Pre-Cleaning & Formatting**: `string_cleaner.py` and `standardizer.py` handle syntax, unicode invisible characters, and casing.
5. **Standardization**: `currency_converter.py` normalizes `$`, `€`, `£` to `₹` (INR). `multilingual.py` translates foreign text to English.
6. **Deduplication**: `deduplication.py` finds exact and fuzzy duplicates. `entity_resolution.py` merges these clusters into complete Golden Records.
7. **Smart Imputation**: `planner_agent.py` writes cross-column rules. `missing_values.py` executes them, falling back to Skewness-based Means/Medians for numeric data, and Modes for categorical.
8. **Outliers**: `outliers.py` clips anomalies using IQR bounds.
9. **Validation**: `validator.py` checks math constraints (e.g., Delivery < Order date), and `ValidationAgent` spot-checks for logic bugs.
10. **Export**: `explanation_agent.py` translates the technical JSON metadata into a Markdown report, exported alongside the clean CSV.

## Development Process
The application was built iteratively, prioritizing extreme memory optimization for low-end hardware (i3 processors, 12GB RAM):
1. **Phase 1**: Built the deterministic Pandas algorithms (`loader`, `cleaners`) using PyArrow to bypass memory limits.
2. **Phase 2**: Intercepted the LLM workflow by building `LMStudioClient` with dynamic model discovery and exponential backoff, preventing hardware timeouts.
3. **Phase 3**: Developed the Multi-Agent architecture, passing highly optimized, minimal data payloads (e.g., only 5 random rows or `pd.unique()` arrays) to the LLM to save tokens and VRAM.
4. **Phase 4**: Integrated the Streamlit frontend with a custom Python callback class to capture `print()` statements and yield them directly to the UI dynamically.

## Frontend UI and Logics Explanation
The user interface is entirely driven by `app.py` using Streamlit.
- **State Management**: The UI is wrapped in `st.session_state` checks. If data is already cleaned, the UI instantly renders cached results instead of forcing a 5-minute backend recalculation.
- **Real-Time Streaming**: The "Pipeline Logs" section is an empty Markdown container. The backend orchestrator is passed a `ui_logger(msg)` function. When the `SchemaAgent` finishes a task, it triggers this logger, physically pushing text into the frontend container.
- **Metrics Dashboard**: After cleaning, the UI parses the `metadata` dictionary to display Delta metrics (e.g., Quality Score went from 60 to 98).
- **Raw HTML Rendering**: The "Imputations" tab uses `st.markdown(unsafe_allow_html=True)` to render raw HTML/CSS `<div>` boxes, giving the app a sleek, glassmorphism aesthetic that standard Streamlit lacks.

## Tools and Techniques Used

### LLMs and Agents
- **Prompt Engineering constraints**: All LLMs are forced to output `{"type": "json_object"}`. Prompts explicitly forbid conversational filler text.
- **Dynamic Context**: Agents are given contextual variables (like the guessed Domain and column data types) before being asked to make decisions.
- **Sampling**: To prevent crashing, the `ValidationAgent` converts a random `df.sample(5)` into JSON, rather than passing a 50,000-row string.

### Cleaning Scripts Features
- **Zero-Width Deletion**: Uses regex `[\u200B-\u200D\uFEFF]` to destroy invisible byte-order marks.
- **Winsorization**: Instead of dropping outlier rows (and losing valuable string data), `np.where()` clips extreme values to the 5th and 95th IQR percentiles.

- **Sorted Neighbourhood Indexing**: To find duplicates without crashing the computer, the system first sorts the entire dataset alphabetically based on a main column like 'Name' or 'Email'. Then, instead of comparing every single row to every other row, it only compares a row to the 7 rows immediately above and below it. Because the list is sorted alphabetically, typos and duplicates are naturally forced to sit right next to each other!
- **Multi-Field Weighted Fuzzy Matching**: Uses `RapidFuzz` Levenshtein distance across Names (40% weight), Emails (40%), and Cities (20%) to confirm duplicates.
- **Primary Row Backfilling**: When merging duplicates, it sorts the cluster by missing values. The row with the *fewest* missing values is kept, and missing fields are backfilled from the deleted secondary rows.

### Memory Optimization Techniques
- **PyArrow C++ Engine**: Bypasses native Pandas C-engine memory bottlenecks.
- **O(1) Token Caching**: `MultilingualEngine` extracts `pd.unique()` strings, sends only those 5 or 10 unique strings to the LLM to translate, and maps the resulting dictionary back to 50,000 rows instantly using vectorization.

## Validation Process
- **Deterministic**: `validator.py` applies hardcoded vector masks to check for negative quantities, taxes, and chronological date violations.
- **Cognitive**: `ValidationAgent` takes a post-clean sample and evaluates it purely for semantic logic (e.g., "Are these merged Names actually two different people?"). The UI alerts the user if the LLM's confidence score drops below 80%.

## Results (Before & After Comparison)
**Before (Raw Data)**:
```csv
Name,Email,City,TotalAmount,OrderDate,DeliveryDate
"Raj Sharma",RAJ.S@test.com,दिल्ली," $ 100",2023-01-01,2022-12-30
"Raj Sharma ",NaN,New Delhi,"€90",NaN,NaN
"Test User",test@test.com,Unknown,-500,NaN,NaN
```

**After (IntelliCleaned)**:
```csv
Name,Email,City,TotalAmount,OrderDate,DeliveryDate
"Raj Sharma",raj.s@test.com,New Delhi,8300.0,2023-01-01,2023-01-05
```
**Explanation of changes**:
- The `Test User` row was permanently dropped by the `QualityFilter`.
- "दिल्ली" was translated to "New Delhi" via `MultilingualEngine`.
- "Raj Sharma " and "Raj Sharma" were fuzzy-matched and merged.
- The `€90` (converted to ₹8100) and `$100` (₹8300) were evaluated. The canonical row was kept.
- `OrderDate` anomaly (delivered before ordered) was flagged by the `Validator`.
- Missing `DeliveryDate` was imputed logically by the `PlannerAgent` (e.g., `OrderDate + 4 days`).

## Limitations
- **Hardware Bottlenecks**: Relies entirely on the speed of the user's Local GPU/CPU. A slow local LLM will cause the pipeline to run slowly.
- **Language Extensibility**: While the LLM can translate dozens of languages, obscure dialects may default to the `unidecode` phonetic transliteration fallback, losing semantic perfection.
- **Fuzzy False Positives**: In extremely dense datasets (e.g., thousands of people named "John Smith" in "New York"), a `FUZZY_MATCH_THRESHOLD` of 85% might accidentally merge two distinct people. This requires the user to tweak `config.py` to 95%.
