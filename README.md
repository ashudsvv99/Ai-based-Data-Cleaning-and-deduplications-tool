# IntelliClean AI: Automated Data Cleaning & Deduplication Tool

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/ashudsvv99/Ai-based-Data-Cleaning-and-deduplications-tool)

Welcome to **IntelliClean AI**, a state-of-the-art framework designed to solve complex data inconsistency challenges in enterprise datasets. Traditional data cleaning scripts struggle with fuzzy deduplication, smart missing value imputation, and context-aware entity handling. IntelliClean AI leverages local Large Language Models (LLMs) and advanced mathematical algorithms to clean, normalize, and deduplicate datasets seamlessly—all while operating completely offline to ensure 100% data privacy.

---

## 🛑 The Problems It Solves
Raw datasets generated from diverse enterprise sources are universally plagued with inconsistencies. Based on rigorous functional requirements, IntelliClean AI directly solves the following critical data engineering problems:

1. **Scattered & Unstructured Ingestion**: Analysts waste hours manually configuring delimiters, encodings, and handling different formats (CSV, XLS, XLSX). This system auto-detects and standardizes ingestion for datasets up to 200MB.
2. **Blind Data Manipulation**: Lack of visibility into data sparsity. This tool solves this by computing total rows, missing percentages, datatypes, and memory usage instantly.
3. **Manual Schema Tagging**: Manually identifying whether a column is a Date, an Entity, or Free Text is tedious. The framework uses local LLMs to dynamically understand the semantic meaning of every column.
4. **"One-Size-Fits-All" Cleaning Failures**: Standard scripts break because they treat a 'Name' column the same as a 'Review' column. The AI agents solve this by tailoring specific cleaning strategies (e.g., Protect -> Normalize -> Transliterate for Entities).
5. **Naive Missing Value Imputation**: Filling blanks with `0` or `Unknown` skews models. IntelliClean uses intelligent inference (Medians, Modes, predictive estimation, and context-aware filling).
6. **Advanced Deduplication Limits**: Standard deduplication only finds exact matches. This system resolves Exact, Partial, Fuzzy (typos), Semantic (`IBM` vs `International Business Machines`), and Cross-Language (`समीप` vs `Sameep`) duplicates dynamically.
7. **Data Destruction via Translation**: Standard translation pipelines destroy Entities (Names, Addresses, IDs). This engine guarantees Entity Preservation while successfully translating free-text columns.
8. **Loss of Secondary Data**: When duplicates are deleted, secondary data is often lost. The system solves this by generating a highly-complete "Canonical Record" that merges the best fields from the duplicate cluster.
9. **The AI "Black Box" Problem**: Users cannot trust automated AI cleaning. The built-in Explainability Module ensures transparency by recording the original value, transformed value, reason for change, and a confidence score for every single modification.

---

## 🌟 What It Can Do (Core Features)

*   **100% Local AI Integration**: Operates completely offline using Local LLMs (via LM Studio), guaranteeing zero data leakage.
*   **Universal Dataset Loader**: Supports **CSV, XLS, and XLSX** files up to **200 MB**, with auto-detection of delimiters, encodings, sheet names, and column headers.
*   **Automatic Dataset Profiling**: Computes total rows/cols, missing values, duplicates, datatypes, and memory usage.
*   **AI-Based Schema Understanding**: Classifies columns intelligently (Entities, Identifiers, Numeric, Temporal, Free Text, Categorical) to apply context-specific strategies.
*   **Agent-Based Cleaning Strategy**: AI agents determine the best pipeline (e.g., Protect entity -> Normalize -> Transliterate -> Fuzzy matching).
*   **O(N) Semantic Deduplication**: Replaces exponential $O(N^2)$ cross-joins with Sorted Neighbourhood Indexing and RapidFuzz.
*   **Entity Preservation**: Never translates entities. Uses normalization, transliteration, and similarity matching instead.
*   **Multilingual Translation**: Automatically detects non-ASCII strings and batch-translates descriptive/free-text columns to English.
*   **Intelligent Missing Value Handling**:
    *   *Numeric*: Median or predictive estimation.
    *   *Categorical*: Mode or relationship inference.
    *   *Entity Fields*: Context-aware placeholders.
*   **Canonical Record Generation**: After clustering duplicates, generates one final representative record.
*   **Intelligent Outlier Handling**: Clips numerical anomalies using IQR bounds (Winsorization) without dropping valuable rows.
*   **Real-Time Explainability Module**: Streams Python logs and AI "thoughts" directly to the UI. Records original value, transformed value, reason for change, and confidence score for every modification.
*   **Export Module**: Outputs Cleaned CSV/Excel, Cleaning Report, Duplicate Report, and Missing Value Report.

---

## ⚙️ Complete Workflow Architecture

1. **Ingestion & Profiling**: Reads data via PyArrow; coerces known missing markers to `pd.NA`. Establishes a baseline Quality Score.
2. **Schema & Domain AI**: Categorizes columns (e.g., Email, Date, Currency) and detects the industry (e.g., Healthcare).
3. **Aggressive Scrubbing**: Drops useless columns (>90% missing) and rows missing critical identifiers.
4. **Pre-Cleaning & Formatting**: Handles syntax, unicode invisible characters (Zero-width deletion), and casing.
5. **Standardization**: Normalizes currencies (`$`, `€`, `£` to `₹`) and translates foreign text to English.
6. **Deduplication**: Finds exact and fuzzy duplicates. Merges these clusters into complete Golden Records via primary row backfilling.
7. **Smart Imputation**: Generates dynamic cross-column rules. Executes them, falling back to Skewness-based Means/Medians/Modes.
8. **Outliers**: Clips anomalies using IQR bounds.
9. **Validation**: Checks math constraints (e.g., Delivery < Order date). ValidationAgent spot-checks for logic bugs.
10. **Export**: Translates technical JSON metadata into a human-readable Markdown report alongside the clean CSV.

---

## 📊 Results: Before & After

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
*   `Test User` dropped by QualityFilter. "दिल्ली" translated to "New Delhi".
*   "Raj Sharma " and "Raj Sharma" fuzzy-matched and merged.
*   Currency converted and canonically merged. Chronological dates fixed/imputed logically.

---

## 🛠️ Technology Stack & Memory Optimization

*   **Frontend**: `streamlit` (Real-time UI rendering with raw HTML/CSS glassmorphism aesthetics).
*   **Data Engineering**: `pandas`, `pyarrow` (High-speed C++ ingestion), `numpy`.
*   **Matching & Deduplication**: `recordlinkage` (Sorted Neighbourhood Indexing), `rapidfuzz` (Levenshtein distance).
*   **String Processing**: `unidecode`, Python `re`.
*   **AI Integration**: `requests` (Local REST API via LM Studio), `pydantic`.

**Memory Optimization (For i3 Processor / 12GB RAM):**
*   **PyArrow Engine**: Bypasses native Pandas memory bottlenecks.
*   **Aggressive Downcasting**: Converts numeric columns (e.g., float64 to float32) and low-cardinality strings to `category` dtypes.
*   **O(1) Token Caching**: Extracts `pd.unique()` strings and sends only unique arrays to the LLM to save tokens and VRAM.

---

## 🚀 Setup & Installation Guide

### 1. Prerequisites
Ensure you have **Python 3.10 or higher** installed on your system. 

### 2. Clone the Repository
```bash
git clone https://github.com/ashudsvv99/Ai-based-Data-Cleaning-and-deduplications-tool.git
cd "Ai based Automated Data cleaning and Deduplication"
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Local AI Engine (LM Studio)
1. Download and install [LM Studio](https://lmstudio.ai/).
2. Download a lightweight Instruct model. Recommended models: **Qwen**, **DeepSeek-R1**, or **Llama 3 8B** in GGUF format (Q4_K_M is recommended for 12GB RAM).
3. Start the **Local Inference Server** within LM Studio. Ensure it runs on the default port: `http://localhost:1234/v1`.

---

## 💡 Usage Guide

1. **Run the App**: Open your terminal in the root directory and execute:
   ```bash
   streamlit run app.py
   ```
2. **Upload Dataset**: Drag and drop your dirty `.csv` or `.xlsx` file into the Streamlit UI. (Try the `Sample datasets/` folder).
3. **Monitor Pipeline Logs**: Watch the AI stream its thought process and schema analysis in real-time.
4. **Review Results**: Navigate the tabs (**Data Quality**, **Imputations**, **Audit Trail**) to inspect AI confidence scores and delta metrics.
5. **Download**: Export the fully cleaned CSV and the Markdown Summary Report.

---

## 📁 Project Structure

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

---

## ⚠️ Limitations

*   **Hardware Bottlenecks**: Processing speed relies entirely on the user's Local GPU/CPU performance.
*   **Language Extensibility**: Obscure dialects may default to phonetic transliteration (`unidecode`) instead of semantic translation.
*   **Fuzzy False Positives**: In extremely dense datasets, the default `FUZZY_MATCH_THRESHOLD` (85%) might merge distinct but similarly-named entities (configurable in `config.py`).

---

## 🔒 Privacy & Security
**Zero Data Leakage:** Because IntelliClean AI uses a local LLM via LM Studio, absolutely no data is sent over the internet. Your sensitive enterprise data remains 100% on your local machine.
