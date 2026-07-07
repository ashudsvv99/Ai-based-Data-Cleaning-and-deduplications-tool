# IntelliClean AI: Complete Technical & Business Documentation

Welcome to the ultimate guide for **IntelliClean AI**. This document is designed to provide a deeply technical, exhaustive breakdown of every rule, logic, LLM prompt, and agent coordination mechanism in the repository, while simultaneously serving as a high-level overview of the project's features and setup.

---

## 1. The Core Problem We Are Solving

In the modern enterprise, data is the most valuable asset. However, raw data exported from CRMs, web scraping tools, or legacy databases is almost always messy, unstructured, and plagued with inconsistencies.

Traditional data cleaning tools and Python scripts fail because they lack "context." For example, a traditional script might blindly translate a French person's name into English, destroying the data. Or, it might fail to realize that `Jon Smith` and `John Smith` are the exact same person because of a simple typo.

**IntelliClean AI solves this by introducing cognitive, context-aware artificial intelligence into the data pipeline.** It seamlessly handles **CSV files, Excel files, and Live SQL Databases**, transforming chaotic datasets into pristine, analytics-ready "Golden Records."

Here is how IntelliClean actively solves the most complex data engineering challenges:

### A. Missing Values (Smart Imputations)
Standard scripts simply fill missing numbers with `0` and missing text with `"Unknown"`. This destroys financial models and statistical integrity.
* **The Solution**: IntelliClean uses contextual **Smart Imputation**. 
* **Example**: If `Delivery_Date` is missing, the AI `PlannerAgent` can dynamically deduce it by writing a rule like `Order_Date + 4 days`. If no rule applies, it mathematically analyzes the column's *skewness*: filling highly distorted salary data with the **Median** (to prevent outliers from ruining the average), and filling normal data with the **Mean**.

### B. Outlier Detection and Cleaning
Standard scripts usually `drop` rows containing extreme outliers, which permanently destroys all the valid secondary data in that row (like the person's Name and Email).
* **The Solution**: IntelliClean uses the **Interquartile Range (IQR)** to mathematically establish upper and lower bounds.
* **Example**: If a user accidentally types an employee's age as `9999`, the system detects it as an anomaly. Instead of deleting the row, it uses **Winsorization (Clipping)** to gently reduce the `9999` back down to the 95th percentile limit (e.g., `85`), perfectly preserving the row's integrity while fixing the math.

### C. Duplicate Values (Exact, Partial, Fuzzy, and Semantic)
Standard scripts use `df.drop_duplicates()`, which only catches 100% identical byte-for-byte rows.
* **The Solution**: IntelliClean resolves four distinct types of duplicates using $O(N)$ Sorted Neighbourhood Indexing and RapidFuzz scoring:
  1. **Exact Duplicates**: Entire rows that match perfectly.
  2. **Partial Duplicates**: Rows differing in only a few empty fields.
  3. **Fuzzy Duplicates**: Typo variations (e.g., resolving `Sameep` vs `Samip` mathematically). *Note: The system is smart enough to temporarily drop exact identifier columns like `transaction_id` during fuzzy matching to prevent accidentally merging valid, unique financial transactions.*
  4. **Semantic Duplicates**: Resolving meaning variations (e.g., mapping `IBM` to `International Business Machines`).

### D. Multilingual Translations and Transliterations (Entity Preservation)
Traditional translation APIs blindly translate everything. If a person's name is "Rose", a blind translator might turn it into the Spanish word "Rosa", altering their legal identity.
* **The Solution**: IntelliClean features strict **Entity Preservation**. 
* **Example (Transliteration)**: The system knows *never* to translate Entities (Names, Addresses). Instead, it uses phonetic **Transliteration**. If it sees the Hindi name `समीप`, it transliterates it to the ASCII equivalent `Sameep`. This allows the Deduplication engine to instantly recognize that `समीप` and `Sameep` are cross-language duplicates of the exact same person!
* **Example (Translation)**: It reserves true *translation* purely for Free Text columns, using $O(1)$ Token Caching to batch-translate foreign reviews into English (e.g., translating "München is great" to "Munich is great").

---

## 2. Features and Functionalities

IntelliClean AI is a state-of-the-art framework designed to solve complex data inconsistency challenges in enterprise datasets. 

- **100% Local AI Integration**: Operates completely offline using Local LLMs (via LM Studio), guaranteeing zero data leakage for HIPAA/GDPR compliance.
- **Universal Data Ingestion (CSV, Excel, Live DB)**: Seamlessly handles offline `.csv`, `.xls`, `.xlsx` files AND live SQL Databases (MySQL, PostgreSQL, SQL Server, etc.) with automatic memory-protection downsampling.
- **Dynamic Multi-Agent System**: Specialized AI agents evaluate schemas, guess business domains, generate dynamic "IF-THEN" rules for missing data, and translate natural language to SQL queries.
- **Multilingual Translation Engine**: Automatically detects non-ASCII strings and batch-translates them to standardized English to preserve deduplication integrity using $O(1)$ token caching.
- **Advanced Fuzzy Deduplication**: Replaces exponential cross-join comparisons with Sorted Neighbourhood Indexing and RapidFuzz, resolving typos and semantic duplicates across millions of rows in seconds.
- **Entity Resolution & Preservation**: Merges duplicate rows into a single "Golden Record" via a backfill cascade, ensuring zero usable data is lost.
- **Intelligent Outlier Handling**: Utilizes IQR bounding and Winsorization (clipping) to normalize numerical anomalies without dropping valuable rows.
- **Real-Time Streaming UI**: Built with Streamlit, the frontend intercepts backend Python logs and AI "thoughts," streaming them directly to the user to eliminate the "black box" effect.

---

## 2. Current Project Structure

```text
IntelliClean/
├── app.py                     # Main Streamlit Frontend
├── pages/
│   └── Live_Database.py       # Live DB Connection & NL Query Console UI
├── config.py                  # Global hyperparameters and API endpoints
├── requirements.txt           # Dependency list
├── agents/                    # The AI Cognitive Engine
│   ├── llm_client.py          # Unified LM Studio HTTP interface
│   ├── schema_agent.py        # Semantic column profiling
│   ├── planner_agent.py       # Imputation rule generation
│   ├── nl_query_agent.py      # Natural language to SQL query generation
│   ├── validation_agent.py    # Post-clean logic auditing
│   └── explanation_agent.py   # Human-readable markdown generation
├── backend/                   # Infrastructure & Orchestration
│   ├── pipeline.py            # Central 12-phase orchestrator
│   ├── loader.py              # PyArrow ingestion & missing value coercion
│   ├── db_connector.py        # SQLAlchemy connector for Live DBs (MySQL, Postgres, etc)
│   ├── schema_detector.py     # Fast heuristic datatype & schema detection
│   ├── domain_profiler.py     # Industry context detection
│   ├── profiler.py            # Baseline statistical calculation
│   ├── validator.py           # Hardcoded math/constraint checks
│   └── exporter.py            # File I/O for reports and CSVs
└── cleaning/                  # The Core Algorithms
    ├── quality_filter.py      # >90% sparsity & dummy data dropping
    ├── datatype_cleaner.py    # Mixed-type normalization and boolean mapping
    ├── multilingual.py        # O(1) Token Caching translation
    ├── currency_converter.py  # Regex symbol extraction & INR mapping
    ├── standardizer.py        # Semantic formatting (lowercase emails, etc)
    ├── string_cleaner.py      # Zero-width char & whitespace removal
    ├── deduplication.py       # Sorted Neighbourhood fuzzy matching
    ├── entity_resolution.py   # Cluster merging and primary row backfilling
    ├── missing_values.py      # AI rule evaluation + Skewness statistical fills
    └── outliers.py            # IQR calculation and Winsorization (Clipping)
```

---

## 3. Setup Guide (Windows & Linux Environments)

### System Prerequisites
* **Python**: Version 3.10 or higher.
* **RAM**: Minimum 12GB recommended.
* **Local LLM**: LM Studio installed locally.

### Step 1: Clone the Repository
```bash
git clone https://github.com/ashudsvv99/Ai-based-Data-Cleaning-and-deduplications-tool.git
cd "Ai based Automated Data cleaning and Deduplication"
```

### Step 2: Create a Virtual Environment

**Windows Environment:**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux Environment (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.10-venv
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure LM Studio
1. Open LM Studio and download a lightweight Instruct model (e.g., **Qwen**, **DeepSeek-R1**, or **Llama 3 8B** in **GGUF Q4_K_M** format).
2. Navigate to the **Local Inference Server** tab.
3. Start the server. Ensure it runs on `http://localhost:1234/v1`. The agents in `llm_client.py` will dynamically detect the loaded model.

### Step 5: Launch the Application
```bash
streamlit run app.py
```
A browser window will open at `http://localhost:8501`.

---

## 4. Deep Dive: Scripts, Rules, Logic, and Agent Coordination

Below is an exhaustive breakdown of every single script in the repository, detailing the exact algorithms, heuristics, API requests, and mathematical formulas used to clean data.

# `app.py` - The Streamlit Frontend Orchestrator

The `app.py` script acts as the main entry point for the entire IntelliClean application. It is built using the Streamlit library. Its primary job is not just to display buttons, but to establish a live, bi-directional pipeline between the user interface and the heavily threaded backend Python agents.

## Full Working Process & Logic

### 1. State Management (`st.session_state`)
Streamlit has a unique execution model: every time a user clicks a button or checks a box, it reruns the entire `app.py` script from line 1.
- **Problem**: If we clean a 50,000-row dataset, and the user clicks a tab, we don't want the script to re-run the 5-minute cleaning process.
- **Solution**: We heavily utilize `st.session_state`. We store the `cleaned_df` and the `metadata` dictionaries inside the session state. At the top of the script, we check `if 'cleaned_df' in st.session_state:`. If it exists, we skip the backend execution and instantly render the results.

### 2. The Bi-Directional Callback Logger (`ui_logger`)
- **Problem**: The backend agents (like `SchemaAgent`) take minutes to run. If they just run silently, the frontend will appear frozen and the user might close the browser.
- **Solution**: We define a custom function `ui_logger(msg)` inside `app.py`. We pass this function as an argument to the `PipelineOrchestrator`. 
- **Action**: Deep inside `backend/pipeline.py`, instead of calling Python's native `print("Detecting schema...")`, it calls `log_callback("Detecting schema...")`. This triggers `ui_logger`, which writes the message into a Streamlit Markdown container (`st.markdown`) on the screen. This allows the user to watch the AI's "thought process" stream in real-time.

### 3. Metric Parsing & Data Visualization
Once the `PipelineOrchestrator` finishes, it returns a massive `metadata` JSON dictionary containing every single action the AI took.
- **Action**: `app.py` parses this dictionary to build the UI tabs.
- For the **Data Quality** tab, it extracts `metadata["quality_score_before"]` and `quality_score_after` and renders visual metric cards using `st.metric(delta=...)`.
- For the **Imputations** tab, it loops through the `metadata["imputation_stats"]` array, extracts the specific rules (e.g., `Mean`, `Median`, `Skewness`), and dynamically renders raw HTML blocks (`<div style="...">`) via `st.markdown(unsafe_allow_html=True)` to create a beautiful, modern glassmorphism aesthetic.


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


# `cleaning/currency_converter.py` - Financial Standardization

In global datasets, revenue columns are frequently corrupted by mixed currencies. One row might say `$100.50`, another `€50,00`, and a third `£20`.
1. Pandas treats this entire column as an `object` (string) instead of a `float64` (number), making it impossible to calculate averages or sums.
2. The values represent completely different economic weights. 

The `CurrencyConverter` script uses Regex and mathematical scalar conversion to solve both problems.

## Full Working Process & Logic

### 1. Regex Symbol Extraction
- **Method**: It loops through columns marked as `currency` by the `SchemaAgent`.
- **Logic**: It uses a Regular Expression `r'([$€£¥₹])'` to search for currency symbols inside every single string in the column.
- **Action**: It extracts the symbol into a new temporary Pandas Series. It then uses `df[col].str.replace(r'[^\d.]', '', regex=True)` to forcefully delete everything from the string *except* digits and decimal points (stripping out commas, letters, and the symbols themselves).

### 2. The Conversion Mapping
- **The Dictionary**: It contains a hardcoded mapping of Exchange Rates to INR (₹): `{"$": 83.0, "€": 90.0, "£": 105.0, "¥": 0.55}`.
- **Action**: It takes the extracted symbols array and maps it to these multipliers. So a row that had a `€` gets a multiplier of `90.0`. A row that had no symbol gets a default multiplier of `1.0`.

### 3. Type Coercion and Multiplication (Vectorization)
- **Logic**: Now that the original column has been stripped of symbols, it looks like pure strings of numbers (e.g., `"100.50"`).
- **Action**: It forces Pandas to convert the column into mathematics: `pd.to_numeric(df[col], errors='coerce')`. If a string was hopelessly corrupted (e.g., `"One Hundred"`), `errors='coerce'` turns it into `pd.NA` rather than crashing the script.
- Finally, it executes `df[col] = df[col] * multipliers`. This mathematically converts the `$100` into `₹8300` in a single, lightning-fast CPU cycle. The column is now standardized and ready for the `OutlierHandler`.


# `cleaning/datatype_cleaner.py`

## Overview
`datatype_cleaner.py` is an aggressive scrubbing phase script executed early in the pipeline. It is responsible for fixing corrupted data types, normalizing booleans, and resolving "mixed-type" columns (columns that accidentally contain both strings and numbers).

## Logic and Architecture

### 1. Mixed-Type Resolution
Pandas struggles significantly when a column has a dtype of `object` but actually contains a mixture of integers, floats, and strings.
- **Action**: The cleaner samples the column. If it finds that >60% of the column can be safely converted to a numeric type (using `pd.to_numeric(errors='coerce')`), it forcefully converts the entire column to numeric. Any string values that fail to convert (like `"N/A"` or `"Unknown"`) are converted to `NaN`, which the pipeline's imputation engine will handle later.
- **Benefit**: Prevents downstream crashes in outlier detection and mathematical validation functions.

### 2. Boolean Mapping
Often, boolean columns are represented ambiguously (e.g., `"Yes"/"No"`, `"Y"/"N"`, `"True"/"False"`, `1/0`).
- **Action**: It detects low-cardinality columns that strictly match boolean intent and maps them explicitly to standard Python `True`/`False` booleans.

### 3. Date Parsing
- **Action**: It aggressively hunts for columns with date-like names (e.g., `dob`, `order_date`) or date-like string formats. When found, it coerces them to standard `datetime64[ns]` formats.


# `db_connector.py` - The Live Database Orchestrator

The `backend/db_connector.py` script serves as the bridge between the IntelliClean framework and external Live SQL Databases. It replaces the traditional CSV/Excel file upload mechanism with a direct connection to enterprise data warehouses.

## Full Working Process & Logic

### 1. Unified Connection Interface
- **Problem**: Different databases (MySQL, PostgreSQL, SQL Server, Oracle) require entirely different connection strings and drivers (e.g., `pymysql`, `psycopg2`, `pyodbc`).
- **Solution**: The script leverages `sqlalchemy` as a unified Object Relational Mapper (ORM) engine. The `DatabaseConnector` class accepts a standard set of credentials (host, port, user, password, dbname, type) and dynamically formats the correct SQLAlchemy `create_engine` URI based on the selected database type.

### 2. Connection Pooling & Resource Management
- **Problem**: Opening and closing database connections for every single query is highly inefficient and can overload the database server.
- **Solution**: The script utilizes SQLAlchemy's built-in connection pooling mechanism. It maintains an active session, allowing the application to execute multiple queries (e.g., fetching schemas, running profiling, executing AI queries) without needing to handshake with the database server multiple times.

### 3. Schema & Metadata Extraction
- **Action**: Once connected, the `get_tables()` and `get_table_schema(table_name)` methods use SQLAlchemy's `inspect()` functionality to dynamically read the database's metadata. 
- It extracts the column names and SQL Data Types (VARCHAR, INT, DATETIME). This information is crucial because the AI (`NLQueryAgent` and `SchemaAgent`) needs to know the exact database structure in order to generate valid SQL queries and imputation strategies.


# `cleaning/deduplication.py` - The Identity Resolver

Finding duplicate rows in a dataset is computationally terrifying. If you have 50,000 rows, comparing every row to every other row to find duplicates requires $50,000^2$ (2.5 Billion) comparisons. A normal Python script will freeze and crash. 

The `DeduplicationEngine` solves this using advanced Record Linkage algorithms.

## Full Working Process & Logic

### 1. The Exact Match Pass (Pandas)
- Before doing expensive fuzzy matching, it simply runs `df.duplicated(keep=False)`. If two rows are 100% identical byte-for-byte, they are instantly grouped.

### 2. Sorted Neighbourhood Indexing (The $O(N)$ Solution)
- **Library used**: `recordlinkage`
- It picks a main identifier column (like `Email` or `First Name`). It sorts the entire dataset alphabetically by this column.
- Now, it only compares a row to the 7 rows directly above and below it (`window=7`). Because the data is sorted alphabetically, duplicates (e.g., "Jon Doe" and "John Doe") will naturally sit right next to each other in the array! This reduces billions of comparisons to just a few thousand.

### 3. Multi-Field Weighted Fuzzy Matching
- **Library used**: `RapidFuzz` (which is written in C++ and is 10x faster than standard `FuzzyWuzzy`).
- **Logic**: Once the index gives us a pair of rows (e.g., Row 5 and Row 6), the engine calculates the Levenshtein Distance (how many character edits it takes to turn string A into string B).
- It doesn't just check one column. It checks `Names`, `Emails`, `Phones`, and `Cities`. It applies weights: Name match = 40%, Email match = 40%, City match = 20%. 
- If the final weighted `similarity_score >= config.FUZZY_MATCH_THRESHOLD` (e.g., 85%), it flags the pair as a duplicate cluster!

### 4. Cluster Formation (`networkx`)
- What if Row A is a duplicate of Row B, and Row B is a duplicate of Row C? 
- We use the mathematical Graph Theory library `networkx`. We treat every row as a "Node" and every duplicate match as an "Edge". 
- We call `nx.connected_components(G)`, which instantly groups A, B, and C into a single massive cluster, ready to be merged by the `EntityResolution` script!


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


# `cleaning/entity_resolution.py` - The Cluster Merger

The `DeduplicationEngine` finds the duplicate rows (e.g., Row 5, Row 10, and Row 12 are all "John Doe"). It groups them into a `cluster`. But now what? We can't just delete Row 10 and 12, because Row 10 might have John's Phone Number, while Row 5 is missing it. 

The `EntityResolution` class mathematically collapses (merges) these clusters into a single, highly-complete "Golden Record".

## Full Working Process & Logic

### 1. Iterating the Clusters
- **Logic**: The engine receives `duplicate_clusters`, which is a list of Pandas DataFrames (each DataFrame represents one group of matched rows).
- It iterates through each cluster. If a cluster has only 1 row, it ignores it.

### 2. Determining the "Primary Row"
- **Problem**: Which row do we keep as the foundation?
- **Solution**: We calculate the "Sparsity" (how many empty cells exist) of every row in the cluster.
- **Logic**: `null_counts = cluster.isna().sum(axis=1)`. This counts the exact number of `pd.NA` gaps in each row.
- **Action**: It sorts the cluster using `.sort_values()` based on this null count. The row with the *lowest* number of missing values is crowned the `canonical_row` (Primary Row). The other rows become `secondary_rows`.

### 3. The Backfill Cascade (Data Preservation)
- **Logic**: We iterate through every column in the dataset.
- **Action**: If the `canonical_row` is missing data for a specific column (e.g., `pd.isna(canonical_row["Phone"])`), it loops through the `secondary_rows`.
- As soon as it finds a secondary row that *does* have a Phone Number, it copies that number into the `canonical_row` and breaks the loop.
- **Why**: This ensures that absolutely zero usable data is lost during the deletion of the duplicates. We extract every piece of value from the duplicates before we delete them!

### 4. Reassembly
- Once the `canonical_row` is perfectly assembled, it is added to a `resolved_rows` list.
- All the original rows that made up the cluster are dropped from the main DataFrame, and the new, single, super-charged `canonical_row` is appended in their place.


# `agents/explanation_agent.py` - The Technical Translator

The `metadata` dictionary tracks thousands of data points: exact rows dropped, fuzzy match threshold percentages, skewness coefficients, and IQR bounds. This is completely unreadable for a non-technical business analyst. The `ExplanationAgent` translates this raw JSON telemetry into a professional, human-readable executive summary.

## Full Working Process & Logic

### 1. Payload Optimization (Trimming the Fat)
- **Problem**: The `metadata` dictionary contains raw data lists (like lists of dropped test emails or sample validation rows). Sending this massive dictionary to the LLM will exceed its Context Window (Token Limit).
- **Solution**: The script runs a preprocessing loop. It copies the `metadata` dictionary and actively deletes large, token-heavy fields:
  - `compact_meta.pop("schema_mapping", None)`
  - `compact_meta.pop("validation_issues", None)` (If they are too long).
- **Why**: The LLM only needs the *statistics* (e.g., "Dropped 5 rows", "Score increased by 20%"), not the raw data itself, to write a summary report.

### 2. Markdown Generation
- **Prompting**: The LLM is instructed to act as a Data Engineering Consultant. It must write a structured report using Markdown (`#`, `##`, `- bullet points`).
- It is instructed to highlight the Delta ($\Delta$): The difference between the `quality_score_before` and `quality_score_after`.
- It is instructed to explain *why* decisions were made (e.g., "We clipped outliers using IQR to preserve row integrity").

### 3. Handoff to Exporter
- The resulting string is purely text. The script returns this Markdown string back to the `PipelineOrchestrator`, which passes it to `exporter.py` to be saved as `reports/cleaning_report.md`.


# `backend/exporter.py` - The I/O Operations Manager

After the `PipelineOrchestrator` completes all algorithmic transformations, the resulting `cleaned_df` and `metadata` must be flushed from volatile RAM to physical storage.

## Full Working Process & Logic

### 1. CSV Data Export
- **Logic**: Uses the native Pandas method `df.to_csv("output.csv", index=False)`.
- **Why**: `index=False` prevents Pandas from writing the arbitrary integer row indices (0, 1, 2, 3) as a completely new, meaningless column in the final CSV file, which often frustrates end-users.

### 2. Reporting I/O
- **Logic**: It checks `if metadata.get("explanation_report")`. 
- **Action**: It uses Python's `os` module to safely create a directory: `os.makedirs(config.REPORTS_DIR, exist_ok=True)`.
- **Why**: If the `reports/` folder doesn't exist on the host machine, Python will throw a `FileNotFoundError` when trying to open a file inside it. `exist_ok=True` prevents a crash if the folder already exists.
- It then opens a file stream `with open(report_path, "w", encoding="utf-8")` and dumps the Markdown string generated by the `ExplanationAgent`. Specifying `encoding="utf-8"` is critical here to ensure any multilingual characters (or emojis) that the LLM generated aren't corrupted when saved to disk.


# `pages/Live_Database.py`

## Overview
`Live_Database.py` is a Streamlit multi-page component that acts as a universal Database Connector and a Natural Language (NL) Query Console. It replaces the old `db_studio.py` and provides a unified interface to connect to databases (PostgreSQL, MySQL, SQL Server, etc.), browse schemas, run the AI Cleaning Pipeline against live tables, and execute plain-English queries.

### 1. Credential Management & Handshake
- **Action**: It renders a secure form for users to input their database Host, Port, Username, and Password. When submitted, it instantiates the `DatabaseConnector` and attempts a handshake. Upon success, it stores the active connection engine in `st.session_state` so the user doesn't have to reconnect upon page refreshes.

### 2. Table Discovery & Selection
- **Action**: It automatically queries the database to discover all available tables. It presents these in a sidebar dropdown, allowing the user to seamlessly switch contexts between different database tables.

### 3. Natural Language Query Console
- Takes natural language questions (e.g., "Show me the top 5 customers by revenue").
- Passes the query and table schema to `NLQueryAgent` to generate an executable `SELECT` SQL query.
- Detects destructive operations and warns the user.
- Executes the query securely and streams results back to a Pandas DataFrame in the UI.

### 4. Live Table Cleaning
- Connects the chosen table directly to the main `PipelineOrchestrator`.
- Fetches a sample of the data (limited to prevent memory crashes) and runs the full 12-phase AI cleaning pipeline.
  - It fetches a 100k-row sample and runs the `DatasetProfiler` to generate missing value matrices and exact duplicate counts.
  - It dynamically invokes the `SchemaDetector` to map semantic types (e.g., `Name`, `ID_Code`).
  - **Fuzzy Deduplication Rule 13**: To find typos in transactional databases, it actively drops exact identifier columns (like `transaction_id`) and maps `Free_Text` to the `fuzzy_name` strategy. It then executes the `DeduplicationEngine` locally to find typographical duplicate clusters (Pass 5) without falsely grouping valid transactions.


# `agents/llm_client.py` - The Universal AI Interface

If all 5 agents (Schema, Planner, Validation, etc.) had to write their own HTTP request logic to talk to LM Studio, the codebase would be bloated and fragile. `LMStudioClient` abstracts all AI communication into a single, highly-resilient utility class.

## Full Working Process & Logic

### 1. Dynamic Model Discovery
- **Problem**: Early versions of this script hardcoded `model="qwen2"`. If the user unloaded Qwen and loaded DeepSeek in LM Studio, every API call would crash with a `ModelNotFoundError`.
- **Solution**: The `__init__` method hits the `http://localhost:1234/v1/models` REST endpoint using `requests.get()`. 
- **Action**: It parses the JSON response, extracts the exact ID of the currently loaded model in RAM (`models["data"][0]["id"]`), and saves it to `self.model_id`. All future POST requests use this dynamic ID, ensuring 100% model-agnostic compatibility.

### 2. Exponential Backoff (Retry Loops)
- **Problem**: Local AI inference runs on the user's GPU. If the GPU gets overloaded, the API will time out or throw a 500 Server Error.
- **Solution**: The `chat_completion_json` method is wrapped in a `for attempt in range(max_retries):` loop.
- **Action**: If a `requests.exceptions.RequestException` occurs, it catches it, prints a warning, and executes `time.sleep(2 ** attempt)`. This means it waits 1 second, then 2 seconds, then 4 seconds. This "exponential backoff" gives the GPU time to clear its VRAM before trying again.

### 3. Strict JSON Enforcement
- **Logic**: We pass `response_format={"type": "json_object"}` in the API payload.
- **Why**: An LLM naturally wants to chat ("Here is your JSON..."). If it outputs conversational text, `json.loads()` will crash. By passing this flag, we trigger the LLM's "Grammar Constrained Decoding". The API physically prevents the LLM from outputting any token that violates JSON syntax.
- **Validation**: After receiving the response, the script runs a regex `re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)` to strip out invisible control characters that sometimes hallucinate, ensuring `json.loads(content)` executes perfectly.


# `backend/loader.py` - The Universal Data Ingestor

Before any algorithmic cleaning can occur, we must load the raw file from the hard drive into RAM. The `UniversalLoader` class is built to aggressively handle the common pitfalls of messy business files (encoding errors, hidden empty strings, massive file sizes).

## Full Working Process & Logic

### 1. PyArrow Backend Optimization
- **Problem**: Reading a 100,000-row CSV file using standard Pandas (`engine="c"`) is single-threaded and notoriously slow, often causing UI freezing.
- **Solution**: We explicitly call `pd.read_csv(self.filepath, engine="pyarrow")`. 
- **Why**: PyArrow is written in C++ and uses multi-threading out of the box. It bypasses Pandas' inefficient object allocation and loads massive files exponentially faster.

### 2. Encoding Fallbacks
- **Logic**: We wrap the initial PyArrow read in a `try-except` block.
- **Why**: PyArrow is incredibly fast, but strict. If a user uploads a CSV saved from an old Windows machine using ANSI encoding (instead of standard UTF-8), PyArrow will crash. The `except` block catches this and safely falls back to standard Pandas using `encoding="utf-8-sig"`.

### 3. Global Missing Value Coercion
- **Logic**: We import `config.MISSING_VALUE_MARKERS`. We run `df.replace(config.MISSING_VALUE_MARKERS, pd.NA)`.
- **Secondary Logic**: We also run `df.replace(r'^\s*$', pd.NA, regex=True)`.
- **Why**: Users often hit the spacebar in Excel and leave a cell "blank". To Python, a string containing `"   "` is not empty—it's a valid string. The Regex replacement targets any string that consists entirely of whitespace and forcefully converts it to `pd.NA`. This guarantees that downstream scripts (like the `QualityFilter`) correctly register the cell as a missing value.

### 4. Memory Footprint Auditing
- **Logic**: It calls `df.memory_usage(deep=True).sum()` and logs the Megabytes. It also explicitly strips leading and trailing whitespaces from the column headers (`df.columns = [str(c).strip() for c in df.columns]`) to prevent downstream KeyErrors when agents try to reference `df["Price"]` but the column is actually named `df["Price "]`.


# `cleaning/missing_values.py` - The Smart Imputation Cascade

A typical novice data script fills missing numbers with `0`, and missing strings with `"Unknown"`. That completely destroys the statistical integrity of the data. The `SmartImputer` uses a strict hierarchy to intelligently cascade down and fill in gaps using Numpy statistics and LLM rules.

## Full Working Process & Logic

### 1. The LLM Logic Pass (Dynamic Cross-Column Imputation)
- **Method**: `_apply_logic_rules()`
- **Logic**: The `PlannerAgent` previously generated dynamic JSON rules (e.g., `{"target_column": "Shipping", "condition": "Weight > 100", "fill_value": 500}`). 
- **Action**: The imputer dynamically builds a Pandas query string and evaluates it using `pd.eval(condition)`. If the condition is true for a specific row, it uses `df.loc[mask, target_column] = fill_value`.
- **Why**: This is the most accurate form of imputation because it uses contextual data from *other* columns to deduce the missing value.

### 2. Statistical Fallback - Numerical Handling (Numpy)
If no AI rules apply, the script moves to statistical math.
- **Method**: `_impute_numeric()`
- **Logic**: It calculates the skewness of the column using `df[col].skew()`. Skewness measures the asymmetry of the data distribution.
- **High Skew (`> 1.0` or `< -1.0`)**: If the data is highly skewed (e.g., Income data where 99% of people make $50k, but one guy makes $1B), the average (Mean) will be horribly distorted. In this case, the script mathematically falls back to filling the gaps with the **Median**, because the median is resistant to extreme outliers.
- **Low Skew (Normal Distribution)**: If the data follows a standard bell curve (like Ages or Heights), it fills the gaps with the **Mean** (Average).

### 3. Statistical Fallback - Categorical Handling
- **Method**: `_impute_categorical()`
- **Logic**: You can't calculate the average of a string like "City".
- **Action**: It calculates the `Mode` (the most frequently occurring string) using `df[col].mode()[0]`. It then replaces all `pd.NA` gaps with this dominant value.

### 4. Tracking
Every time `df[col].fillna()` is executed, the script updates a central dictionary tracking exactly how many rows were filled, what method was used (`fill_median`, `fill_mode`), and what the statistical properties (Mean, Max, Min) of the column were. This dictionary is exported to the UI so the user can verify the math.


# `cleaning/multilingual.py` - The Scalable Translation Engine

In a global dataset, a user might enter their city as "München" or "म्यूनिख" instead of "Munich". If you don't translate these to a standard language (English), the Deduplication engine will fail to recognize them as duplicates, and categorizations will be fractured. 

The `MultilingualEngine` class translates the dataset, but does so with extreme token caching to avoid crashing the LLM.

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


# `nl_query_agent.py` - The Text-to-SQL Cognitive Agent

The `agents/nl_query_agent.py` script is a specialized LLM agent responsible for translating plain English questions from the user into executable SQL queries against their live database.

## Full Working Process & Logic

### 1. Contextual Prompting
- **Action**: When a user asks a question (e.g., "Find duplicate records"), the agent requires context to generate valid SQL. 
- The script fetches the live database schema (Table Names, Column Names, and SQL Types) and injects it into a massive System Prompt. It strictly instructs the LLM to act as a Senior SQL Developer and *only* output valid SQL that matches the specific schema.

### 2. JSON Block Extraction
- **Problem**: Local LLMs (especially instruction-tuned ones) have a bad habit of wrapping their SQL in markdown blocks (e.g., \`\`\`sql SELECT * FROM table \`\`\`) or adding conversational filler like "Here is your query:".
- **Solution**: The agent utilizes regex and string parsing techniques to aggressively strip out the markdown and conversational text, isolating the raw, executable SQL string.

### 3. The Self-Correction Loop (Error Recovery)
- **Problem**: AI hallucination might cause the LLM to generate SQL with a syntax error or reference a column that doesn't exist.
- **Solution**: If the `db_pipeline.py` fails to execute the query, it catches the SQLAlchemy Database Error. The `NLQueryAgent` takes that exact error message, feeds it *back* into the LLM as a new prompt ("Your previous query failed with this error. Fix it."), allowing the AI to debug and self-correct its own SQL autonomously.


# `cleaning/outliers.py` - The Anomaly Handler

What happens if someone accidentally types `999999` for an employee's age? It ruins every chart and average calculation you try to make. The `OutlierHandler` class finds these extreme anomalies and normalizes them.

## Full Working Process & Logic

### 1. The Interquartile Range (IQR) Method
We don't use ML libraries (like Scikit-Learn Isolation Forests) because they are too slow and opaque for simple business tabular data. We use raw statistics.
- **Logic**: We calculate `Q1` (the 25th percentile of the data) and `Q3` (the 75th percentile) using Pandas `.quantile(0.25)`.
- **The IQR**: `IQR = Q3 - Q1`. This represents the "middle 50%" of all data, immune to the extreme edges.
- **The Bounds**: We establish a mathematical ceiling and floor.
  - `lower_bound = Q1 - (IQR_MULTIPLIER * IQR)`
  - `upper_bound = Q3 + (IQR_MULTIPLIER * IQR)`
- `IQR_MULTIPLIER` is imported from `config.py` (default `1.5`). Anything falling outside these bounds is mathematically defined as an outlier.

### 2. Clipping vs. Dropping (`np.where`)
- **The Novice Mistake**: A junior developer will write `df = df[df['Age'] < upper_bound]`. This *drops* the entire row. This is catastrophic. You just lost that employee's Name, Email, and Phone Number just because their Age had a typo.
- **The Professional Solution (Clipping)**: We import Numpy.
- **Logic**: `df[col] = np.where(df[col] > upper_bound, upper_bound, df[col])`.
- **Action**: `np.where` acts like a vectorized IF-THEN statement. IF the Age is greater than `85` (the upper bound), replace it with exactly `85`. Otherwise, leave it alone.
- **Why**: This technique is called **Winsorizing**. It removes the extreme statistical distortion (the `999999` average destroyer) while perfectly preserving the rest of the row's valuable data.


# `backend/pipeline.py` - The Central Orchestrator

Think of the `PipelineOrchestrator` as the General Manager of a factory. It doesn't actually perform the mathematical algorithms itself, but it imports all the disparate classes (`QualityFilter`, `DeduplicationEngine`, `SmartImputer`) and forces them to execute in a strict, chronological sequence.

## Full Working Process & Logic

### 1. Central State Management
- **Logic**: It initializes a massive dictionary: `self.metadata = {"schema_mapping": {}, "imputation_stats": [], ...}`.
- **Why**: As data moves from one phase to the next, scripts need context. The `SmartImputer` needs to know what the `SchemaAgent` decided in Phase 2. By passing this `self.metadata` dictionary sequentially down the line, every script has access to the full historical context.

### 2. The 12-Phase Execution Hierarchy
The `execute()` method runs a rigid `try-except` wrapped sequence:
1. **Phase 1: Ingestion**: Calls `UniversalLoader` to read the CSV into a Pandas `df`.
2. **Phase 1.5: Profiling**: Calls `DataProfiler` to calculate the starting Quality Score (0-100).
3. **Phase 2: Semantic AI**: Passes the `df` to `SchemaAgent` to classify columns (`email`, `currency`).
4. **Phase 3: Domain AI**: Calls `DomainProfiler` to detect the industry (e.g., `Healthcare`).
5. **Phase 3.5: Quality Filtering**: Calls `QualityFilter.filter_useless_data()` to aggressively nuke >90% empty columns and missing critical rows.
6. **Phase 4 & 5: Format & Translate**: Runs `StringCleaner`, `CurrencyConverter`, and `MultilingualEngine`. (These must run *before* deduplication so that strings are standardized).
7. **Phase 6 & 8: Deduplication**: Runs `DeduplicationEngine` and `EntityResolution` to merge duplicate rows.
8. **Phase 7: Imputation Planning**: Passes the schema to `PlannerAgent` to write JSON "IF-THEN" rules.
9. **Phase 9 & 10: Mathematical Fills**: Runs `SmartImputer` (using the LLM rules and statistical Means) and `OutlierHandler` (IQR clipping).
10. **Phase 11: Validation**: Passes the cleaned `df` to the `Validator` for mathematical hard-checks, and `ValidationAgent` for AI logical auditing.
11. **Phase 12: Export**: Calls `exporter.py` to write the final `.csv` and Markdown reports.

### 3. Graceful Error Handling
Each phase is wrapped in a dedicated `try-except Exception as e:` block. If the Multilingual Translation engine crashes because an API timeout occurred, the Orchestrator logs the error (`log(f"Phase 5 Failed: {e}")`) and simply skips to Phase 6. This guarantees that one minor failure doesn't destroy the user's entire dataset cleaning session.


# `agents/planner_agent.py` - The Strategy Generator

When "Shipping Cost" is blank, you can't just fill it with `0`. You need context. The `PlannerAgent` acts as a Senior Data Scientist, dynamically generating cross-column business rules based on the dataset's specific context.

## Full Working Process & Logic

### 1. Contextual Assembly
- **Logic**: It gathers three critical pieces of context:
  1. `columns_info`: A list of columns and their missing data percentages (calculated by `profiler.py`).
  2. `schema_mapping`: The semantic types (generated by `SchemaAgent`).
  3. `domain`: The industry context (e.g., `Retail`, generated by `DomainProfiler`).
- **Why**: The LLM needs to know that this is a *Retail* dataset, and that `Shipping` is a *Currency* column missing *10%* of its data.

### 2. Prompt Engineering & Constraint Framing
- The agent loads a massive prompt template from `prompts/planner.txt`.
- **The Constraints**: The prompt strictly enforces that the LLM must generate rules using Pandas `pd.eval()` compatible syntax. 
- Example condition it is taught to write: `Weight > 100` (Not `if weight is heavy`). 
- Example fill value: `500` (Not `$500`).

### 3. JSON Parsing and Sanitization
- The LLM returns a JSON list of objects: `[{"target_column": "Shipping", "condition": "Weight > 100", "fill_value": 500}]`.
- **Validation Loop**: The `PlannerAgent` loops through the LLM's rules and cross-checks them against `df.columns`. 
- **Action**: If the LLM hallucinated a column (e.g., `condition: "Distance > 50"`, but "Distance" doesn't exist in the CSV), the script deletes the rule to prevent a crash downstream. 
- The sanitized list of JSON rules is added to `metadata["imputation_rules"]` so the `SmartImputer` can mathematically execute them later.


# `backend/profiler.py` - The Statistical Baseline Calculator

Before we alter a single byte of data, we need a mathematical baseline. The `DataProfiler` calculates raw statistical metrics (Missing Percentages, Duplicate Counts) and computes an overall "Quality Score" out of 100.

## Full Working Process & Logic

### 1. Missing Value Auditing
- **Method**: `_calculate_missing()`
- **Logic**: It creates a boolean mask of the entire dataset using `df.isna()`. It calls `.sum()` to count the exact number of `pd.NA` cells.
- It calculates `missing_pct = (total_missing / (total_rows * total_columns)) * 100`. 
- **Why**: By getting the percentage of missing data across the entire matrix (not just row-by-row), we get a global perspective of data sparseness.

### 2. Exact Duplicate Auditing
- **Method**: `_calculate_duplicates()`
- **Logic**: It uses Pandas vectorization `df.duplicated(keep='first').sum()`. 
- **Why**: This does *not* do fuzzy matching. It mathematically hashes every row and compares it. If two rows are exact bit-for-bit copies of each other, it counts them.

### 3. The Quality Score Formula
- **Logic**: `score = 100.0 - (missing_pct * 1.5) - (duplicate_pct * 2.0)`
- **Why these weights?**: The formula penalizes exact duplicates slightly harder (`2.0` multiplier) than missing values (`1.5` multiplier). Why? Because a missing value is just incomplete data, but a duplicate row actively distorts financial metrics (e.g., doubling revenue by accident). The final score is clipped `max(0, min(100, score))` to ensure it always renders beautifully in the UI between 0 and 100.


# `cleaning/quality_filter.py` - Multi-Dimensional Junk Scrubber

Why waste expensive AI tokens and processing power trying to "clean" a row that is entirely blank? The `QualityFilter` class acts as the bouncer of the pipeline, aggressively dropping useless data *before* any cleaning begins.

## Full Working Process & Logic

The `filter_useless_data()` method executes a multi-dimensional scrub using Pandas vectorization for maximum speed.

### 1. Column-Level Sparsity Check
- **Logic**: `col_thresh = int(len(df_clean) * 0.1)`
- **Action**: It calculates a threshold representing 10% of the total rows. It then calls `df_clean.dropna(axis=1, thresh=col_thresh)`.
- **Why**: If a column has 10,000 rows, but 9,500 of them are `pd.NA` (95% missing), that column provides zero statistical value. It drops the entire column permanently.

### 2. Row-Level Sparsity Check
- **Logic**: `threshold = len(df_clean.columns) // 2`
- **Action**: It requires a row to have at least half of its columns filled with valid data to survive (`df.dropna(thresh=threshold)`).
- **Why**: If a row has 30 columns, but 20 of them are blank, it's a corrupted record.

### 3. Critical Identifier Check (Domain Agnostic)
- **Logic**: The script iterates through `df_clean.columns` and cross-references them against a `critical_keywords` list (`["email", "phone", "city", "address", "name"]`). It also checks the `schema_type` mapped by the `SchemaAgent`. 
- **Action**: If it finds multiple critical columns in the dataset, it calculates `min_required = len(critical_cols) - 1`. It then runs `df.dropna(subset=critical_cols, thresh=min_required)`.
- **Why**: If a record is missing BOTH an Email AND a Phone Number, it's completely unrecoverable for business purposes. The LLM shouldn't be asked to hallucinate a fake phone number to save the row. This mathematically forces the drop.

### 4. Explicit Test / Dummy Data Filter
- **Logic**: Developers often leave fake data in databases (e.g., `Test User`, `test@test.com`, `Unknown Customer`).
- **Action**: It selects all string columns using `df.select_dtypes(include=['object', 'string'])`. It builds a Regex pattern: `r'^(test\s*user|test@|unknown\s*customer|dummy\s*data)$'`.
- It loops through the string columns, applying `.str.match(dummy_pattern, na=False)` to build a Boolean mask. Finally, it drops the rows using inverse masking `df_clean[~mask]`.

### 5. Reporting
It maintains a `self.stats` dictionary tracking exactly how many rows were dropped by *which* rule, returning a formatted string in `get_report()` so the UI can display the exact casualties.


# `agents/schema_agent.py` - The Semantic Profiler

Python natively understands data types like `int64` and `object`. But Python doesn't know that an `object` is actually an "Email Address". The `SchemaAgent` acts as the cognitive bridge, applying semantic meaning to every column so downstream tools know how to clean them.

## Full Working Process & Logic

### 1. The Heuristic Pre-Filter
Calling the LLM for all 30 columns of a dataset is slow. We use fast Python regex and logic to guess the obvious ones.
- **Logic**: Iterates over columns and checks the Pandas `dtype`. 
- If `pd.api.types.is_datetime64_any_dtype(df[col])` is true, it instantly classifies it as `date`.
- If the column name contains the word `amount` or `price`, and the data is numeric, it flags it as `currency`.
- If it contains `email` or the string values frequently contain `@`, it flags it as `email`.
- If it cannot guess, it marks the column as `"unknown"`.

### 2. LLM Fallback (Semantic Inference)
If the heuristic marks a column as `"unknown"` (e.g., a column confusingly named `Val1`), we summon the LLM.
- **Sampling**: We don't send the whole column. We run `df[col].dropna().astype(str).head(5).tolist()` to grab 5 random valid samples.
- **Prompting**: We build a prompt passing the column name and the 5 samples. We instruct the LLM to choose from a strict Enum list: `[categorical, text, email, phone_number, currency, numeric, date]`.
- **Action**: The LLM analyzes the semantic structure (e.g., "These numbers look like Zip Codes") and returns a JSON object classifying the column.

### 3. The Central Schema Dictionary
- The final output is a dictionary mapping: `{"Price": "currency", "Email_Address": "email"}`.
- This dictionary is stored in the `PipelineOrchestrator`'s central `metadata`.
- **Why this is critical**: Later, when `standardizer.py` runs, it checks this dictionary. If a column is an `email`, it runs `str.lower()`. Without the `SchemaAgent`, the standardizer would have no idea what logic to apply!


# `backend/schema_detector.py`

## Overview
`schema_detector.py` is a highly optimized heuristic pre-filter used to infer the semantic category of DataFrame columns *before* relying on the LLM `SchemaAgent`. 

## Logic and Architecture
By using fast regex and string matching to identify obvious column types (e.g., Dates, Emails, URLs, Currencies, Phone numbers), this script saves significant computational time and LLM token usage.

### 1. The Heuristic Filters
The `HeuristicSchemaDetector` tests a small sample (typically 10-20 non-null values) of a column against strict rules:
- **Email**: Uses regex to find `something@something.domain`.
- **URL**: Uses regex to find `http://` or `www.`.
- **Date**: Uses `pd.to_datetime` with `errors='coerce'` to see if >80% of values are valid timestamps.
- **Currency**: Checks for monetary symbols (`$`, `€`, `£`, `₹`) or currency codes (`USD`, `EUR`).
- **Phone**: Checks for dial codes (`+91`, `+1`) or consecutive digits matching phone patterns.
- **Categorical**: If a text column has very few unique values relative to its size (low cardinality), it is flagged as categorical.

### 2. LLM Fallback
If the heuristic filter returns `Unknown` or `Free Text` (because the column is ambiguous, like a 'Name' or 'Address' column), the system will seamlessly pass that specific column to the LLM-based `SchemaAgent` for deeper semantic analysis. This hybrid approach guarantees both speed and accuracy.


# `cleaning/standardizer.py` - The Semantic Formatter

The `StringCleaner` class handles invisible characters and whitespaces, but it doesn't know *what* a string is. The `Standardizer` class receives the semantic mapping from the `SchemaAgent` (e.g., this column is an `email`, that one is a `name`) and applies strict typographical formatting.

## Full Working Process & Logic

### 1. The Schema Mapping Loop
- **Logic**: It iterates over `self.schema_mapping.items()`. It looks at every column and checks its assigned `SemanticType`.
- **Why**: You cannot apply `.str.title()` to every string column. If you title-case an email address (`John.Doe@Gmail.Com`), it technically becomes invalid because domain specifications often expect lowercase.

### 2. Email Standardization
- **Logic**: If `col_type == SemanticType.EMAIL`:
- **Action**: It executes `df[col].str.lower()`. 
- **Why**: Email addresses are mathematically case-insensitive. Standardizing them to pure lowercase ensures that `john@test.com` and `JOHN@TEST.COM` are viewed as identical strings by the Deduplication Engine later on.

### 3. Name and Location Formatting
- **Logic**: If `col_type in [SemanticType.NAME, SemanticType.LOCATION, SemanticType.CATEGORICAL]`:
- **Action**: It executes `df[col].str.title()`. 
- **Why**: "new york" becomes "New York". "jane doe" becomes "Jane Doe". This is purely for downstream reporting aesthetics and ensuring fuzzy-matching algorithms have a standardized baseline to compare against.

### 4. Phone Number Extraction
- **Problem**: Phone numbers are typed in hundreds of formats: `(555)-123-4567`, `+1 555 123 4567`, `555.123.4567`.
- **Logic**: If `col_type == SemanticType.PHONE_NUMBER`:
- **Action**: It uses Regex: `df[col].str.replace(r'[^\d+]', '', regex=True)`.
- **Why**: This Regex string `[^\d+]` means: "Find anything that is NOT a digit (`\d`) and NOT a plus sign (`+`) and replace it with nothing (`''`)". It instantly deletes all parentheses, dashes, and periods, resulting in a clean, uniform string like `+15551234567`.


# `cleaning/string_cleaner.py` - The Invisible Bug Killer

When users copy and paste data from websites (like an HTML table), they frequently drag in "invisible" characters. These include trailing spaces, zero-width spaces (`\u200B`), and non-breaking spaces (`\xA0`).
- **The Problem**: To human eyes, `"John"` and `"John "` look identical. But to Python, `"John" == "John "` evaluates to `False`. This breaks grouping, aggregations, and exact-match deduplication.

## Full Working Process & Logic

### 1. Targeting the Right Data Types
- **Logic**: It executes `cols = df.select_dtypes(include=['object', 'string']).columns`.
- **Why**: You cannot run `.str.strip()` on a column filled with integers (`int64`). It will throw an `AttributeError`. Selecting only the string columns prevents the script from crashing when it hits a math column.

### 2. Multi-Pass Sanitization
The script executes three distinct Pandas vectorization passes over the text:

1. **The Unicode Assassin**: 
   - `df[col].str.replace(r'[\u200B-\u200D\uFEFF]', '', regex=True)`
   - **Why**: This targets Zero-Width spaces and Byte Order Marks. These are literal invisible characters that break algorithms without the developer ever seeing why.

2. **The Newline Crusher**:
   - `df[col].str.replace(r'[\r\n\t]+', ' ', regex=True)`
   - **Why**: If a user hit `Enter` inside an Excel cell, it creates a newline `\n`. This converts all tabs and newlines into a single standard space so the data fits on one line.

3. **The Standard Strip**:
   - `df[col].str.strip()`
   - **Why**: Finally, it removes normal spacebar characters from the far left and far right of the string.


# `agents/validation_agent.py` - The Cognitive Auditor

While `validator.py` catches hard math errors (like Negative GST), it cannot catch semantic or logical anomalies. If the `DeduplicationEngine` accidentally merged "John Smith" (a 20-year-old in NY) with "John Smith" (an 80-year-old in LA), the math is fine, but the logic is broken. The `ValidationAgent` acts as a cognitive QA auditor to spot these complex anomalies.

## Full Working Process & Logic

### 1. The Post-Clean Sampling
- **Logic**: We cannot send a 100,000-row cleaned dataset to a local LLM. It would cause a catastrophic Memory Error.
- **Action**: It executes `sample = df.sample(min(num_samples, len(df))).to_dict(orient="records")` (usually 5 rows). 
- **Why**: By converting a random 5-row sample into a Python dictionary, we create a highly compact JSON string that represents the final state of the cleaned data.

### 2. The Audit Prompt
- It loads `prompts/validation.txt`. 
- The prompt instructs the LLM to adopt the persona of a Senior Data Auditor. It asks the LLM to review the sample and explicitly look for:
  - Formatting inconsistencies (e.g., did a string cleaner miss a weird character?).
  - Logical paradoxes (e.g., are the ages realistic? Are the emails valid domains?).
  - Suspicious Imputations (e.g., did an imputation rule fill a column with a value that doesn't make sense contextually?).

### 3. Confidence Scoring
- The LLM is forced to output JSON containing a `"confidence_score"` (0 to 100) and an `"issues"` array.
- **Integration**: The script extracts this score and appends the issues to `metadata["validation_issues"]`. In the Streamlit UI, if this score is below 80%, the "Data Quality" tab renders in yellow/red to warn the user that the AI itself believes the cleaning pipeline might have made a mistake and requires human review.


# `backend/validator.py` - The Mathematical Constraint Checker

While Artificial Intelligence (`ValidationAgent`) is excellent at spotting semantic weirdness ("Does this name look fake?"), Large Language Models are notoriously terrible at hard mathematics and relational logic. The `BusinessRuleValidator` is a pure Pandas script that executes rigid boolean math checks to catch logic bugs.

## Full Working Process & Logic

### 1. Case-Insensitive Column Mapping
- **Problem**: In a retail dataset, the quantity column might be named `Quantity`, `quantity`, or `QUANTITY`. If we hardcode `df["quantity"] <= 0`, it will throw a `KeyError` and crash the program if the casing doesn't match perfectly.
- **Solution**: The script builds a translation dictionary: `col_map = {c.lower(): c for c in df.columns}`. 
- **Action**: When checking a rule, we look for `"quantity" in col_map`. If it exists, we extract the true column name using `true_col = col_map["quantity"]` and run our math on `df[true_col]`. This entirely prevents KeyErrors.

### 2. Pandas Boolean Masking (Vectorization)
The validator checks thousands of rows in milliseconds using boolean masks.
- **Negative Values**: It applies `mask = pd.to_numeric(df[col], errors="coerce") <= 0`. It counts the `True` values. If `count > 0`, it logs a critical issue: `"Found {count} negative/zero values in '{col}'"`.
- **Relational Logic (Date Checks)**: If it finds both an `order_date` and a `delivery_date` column, it converts both to Pandas Datetime objects using `pd.to_datetime()`. It then runs the mask `mask = df[delivery_col] < df[order_col]`. If it finds a delivery date that happens *before* an order was even placed, it flags it as a logical paradox.

### 3. Aggregation and Logging
Every time a mask returns `> 0` violations, the script appends a formatted string to an `issues` list. This list is injected directly into the final `metadata` dictionary and rendered in the UI with a red warning box, alerting the analyst to manually review those specific mathematical breaks.


