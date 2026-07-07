# Project Requirements

## Functional Requirements

### 1. Universal Dataset Loader & Database Integration
*   **Supported File Formats**: CSV, XLS, XLSX up to **200 MB**.
*   **Auto-Detection**: Automatically detect delimiter, encoding, sheet names, and column headers.
*   **Live Database Connection**: Support connection to major SQL databases (MySQL, PostgreSQL, SQL Server, Oracle, DB2, SQLite).
*   **Database Sampling (OOM Protection)**: Automatically sample massive databases down to 100,000 rows to prevent Out-Of-Memory (OOM) failures on limited hardware.

### 2. Automatic Dataset & Database Profiling
The system shall compute:
*   Total rows and columns.
*   Missing values and null percentages (including grid-based visualizations).
*   Duplicate rows and columns (Exact Duplicates).
*   Datatype distribution and Unique value counts.
*   Memory usage.

### 3. AI-Based Schema Understanding
The framework shall first use a purely heuristic pre-filter (`schema_detector.py`) to fast-track obvious datatypes without using LLM tokens. Then, it shall use the local LLM to determine the semantic meaning of complex columns, classifying them into:
*   **Entity Columns**: Person Name, Company, Product, Brand, City, State, Country, Address.
*   **Identifier Columns**: Customer ID, Email, Phone, PAN, Aadhaar, Order ID.
*   **Numeric**: Price, Salary, Revenue, Age, Quantity.
*   **Temporal**: Date, Timestamp, Order Date, Birth Date.
*   **Free Text**: Reviews, Description, Comments, Feedback.
*   **Categorical**: Status, Gender, Category, Department.

### 4. Agent-Based Cleaning Strategy
An AI agent must determine the best cleaning pipeline per column.
*   *Example (Entity)*: Protect entity -> Normalize -> Transliterate if needed -> Fuzzy matching.
*   *Example (Free Text)*: Translate -> Normalize -> Semantic comparison.

### 5. Missing Value Handling
*   **Numeric**: Median or predictive estimation.
*   **Categorical**: Mode or relationship inference.
*   **Entity Fields**: Unknown placeholders or inference only when supported by strong evidence.
*   **Free Text**: Context-aware filling or leave missing.

### 6. Duplicate Detection
The system must detect:
*   **Exact Duplicates**: Entire row matches.
*   **Partial Duplicates**: Records differing in only a few fields.
*   **Fuzzy Duplicates**: Typo variations (e.g., `Sameep` vs `Samip`). Must ignore exact matches on IDs (like `transaction_id`) to avoid false positives on transactional data.
*   **Semantic Duplicates**: Meaning variations (e.g., `IBM` vs `International Business Machines`).
*   **Cross-Language Duplicates**: Transliteration matches without translation (e.g.,  `समीप` vs `Sameep`).

### 7. Natural Language to SQL (NL Query Engine)
*   **AI-Powered Querying**: Convert plain English questions into executable SQL queries against live databases.
*   **Safe Execution**: Run generated queries dynamically in a read-only context (SELECT queries), preventing accidental database modification.
*   **Error Recovery**: Automatically capture SQL execution errors and pass them back to the LLM for self-correction.

### 8. Entity Preservation Engine
*   **Rule**: Never directly translate names, organizations, products, IDs, emails, phone numbers, or addresses.
*   **Action**: Use normalization, transliteration, canonicalization, and similarity matching instead.

### 9. Translation Engine
*   Only descriptive/free-text columns (reviews, descriptions, comments) shall be translated.

### 10. Canonical Record Generation
*   After clustering duplicates, generate one final representative record (e.g., `John`, `John Smith`, `J. Smith` becomes `John Smith`).

### 11. Explainability Module
Every modification must record:
*   Original value.
*   Transformed value.
*   Reason for change.
*   Confidence score.
*   Responsible agent.

### 12. Export Module
Provide outputs as:
*   Cleaned CSV / Excel.
*   Cleaning Report.
*   Duplicate Report.
*   Missing Value Report.

## Non-Functional Requirements & Hardware Constraints
*   **Hardware Target**: Must run smoothly on an Intel i3 Processor with 12GB RAM.
*   **Performance / Deduplication**: 
    *   $O(N^2)$ cross-joins are strictly prohibited. 
    *   Fuzzy matching must be preceded by a blocking/indexing strategy using `recordlinkage` to ensure CPU load remains acceptable on the i3.
*   **Performance / Memory**: 
    *   Pandas must use `pyarrow` backend for string types.
    *   Numeric columns must be aggressively downcasted (e.g., float64 to float32).
    *   Low-cardinality string columns must be converted to `category` dtypes to keep total memory usage well within the 12GB RAM limit during transformations.
*   **Local Execution**: Must run locally and entirely offline. No cloud dependency.
*   **LLM Constraints**: Local inference must use highly quantized models (GGUF Q4_K_M formats). LLM payloads must be severely restricted (metadata + max 3 rows of data) to prevent CPU timeouts.
*   **Privacy**: Zero data leakage; all inference happens locally.
*   **Usability**: User-friendly Streamlit interface.
