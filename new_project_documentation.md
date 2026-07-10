# IntelliClean AI: Comprehensive Software Documentation Manual

This document serves as the complete technical and user manual for IntelliClean AI. It details every interface, backend script, and AI algorithm utilized across the data cleaning and deduplication lifecycle.

---

## 1. Main Dashboard (CSV/Excel Mode)

### [Add Image Here: Main Dashboard]

### 1.1 Overview
The Main Dashboard is the central entry point of IntelliClean AI for file-based processing. It provides users with a unified workspace for uploading flat-file datasets, monitoring data quality, executing the AI cleaning pipeline, and downloading the cleaned outputs. Built on Streamlit, it serves as the orchestration layer between the frontend UI and the robust Python backend.

### 1.2 Purpose
* Upload `.csv`, `.xls`, and `.xlsx` files securely.
* Configure AI cleaning parameters and pipeline toggles.
* Trigger the 12-phase automated cleaning workflow.
* Monitor real-time execution progress.
* Access generated health profiling reports.
* Download finalized cleaned datasets and audit reports.

### 1.3 UI Components
| Component | Description |
| :--- | :--- |
| **Upload Dataset Dropzone** | Drag-and-drop area for ingesting CSV/XLSX files into memory. |
| **Dataset Preview Grid** | Interactive table displaying the first 100 rows of the ingested file. |
| **Health Profiler Module** | Visual dashboard highlighting data quality issues prior to cleaning. |
| **AI Pipeline Trigger** | Button to start the intelligent 12-phase cleaning pipeline. |
| **Download Section** | Action buttons to export the cleaned CSV, Excel file, or JSON Audit Report. |

### 1.4 Internal Working
When a file is uploaded, the following sequence occurs:
1. `UniversalLoader` ingests the dataset into memory.
2. `pandas` (with pyarrow backend) parses the file structure.
3. Missing markers (e.g., `"N/A"`, `""`, `"null"`) are converted to standard `np.nan`.
4. Memory optimization techniques are applied to downcast data types.
5. The `DatasetProfiler` begins statistical analysis.
6. The `SchemaAgent` engages the LLM to identify semantic column intents.
7. The `PlannerAgent` formulates a customized cleaning strategy based on the profile.
8. The `PipelineOrchestrator` begins sequential execution.

### 1.5 Backend Scripts Used
* `pages/CSV_Excel_Mode.py` (Frontend UI)
* `backend/loader.py` (Ingestion)
* `backend/profiler.py` (Statistical analysis)
* `agents/schema_agent.py` (LLM intent detection)
* `agents/planner_agent.py` (Strategy formulation)
* `backend/pipeline.py` (Execution orchestration)

### 1.6 User Workflow
Upload File &rarr; Preview Dataset &rarr; View Health Score &rarr; Click "Clean Dataset" &rarr; Pipeline Starts &rarr; Results Displayed &rarr; Download Files.

### 1.7 Screenshot Explanation
* **File Uploader:** The dashed box at the top where users drop their files.
* **Preview Table:** The dataframe rendered in the center showing raw data.
* **Global Config Sidebar:** The left-hand panel allowing the user to select the LLM endpoint (Local LM Studio vs Cloud) and adjust temperature settings.

---

## 2. Health Profiler

### [Add Image Here: Health Profiler Dashboard]

### 2.1 Overview
The Health Profiler acts as the diagnostic engine of IntelliClean AI. Before any cleaning occurs, it deeply analyzes the raw dataset to surface anomalies, null values, and structural defects.

### 2.2 Purpose
* Scan the dataset for exact duplicate rows.
* Calculate total missing cells and compute a global "Quality Score".
* Generate a missing-value heatmap for visual density analysis.
* Provide granular column-level statistics (mean, median, unique counts).
* Detect character scripts (e.g., Latin vs. Devanagari) for multilingual processing.

### 2.3 Key Features & Algorithms
* **Missing Values Analysis:** Iterates over the dataframe to sum `isnull()` and calculate percentage nulls.
* **Duplicate Detection:** Uses pandas `.duplicated()` to find exact 1:1 row copies.
* **Script Detection:** Applies regex blocks to determine if text columns contain Arabic, Cyrillic, or Devanagari characters, flagging them for translation later in the pipeline.
* **Quality Score Algorithm:** A weighted deduction formula starting at 100%. Deducts points based on the ratio of missing cells, exact duplicates, and mixed-data types.

### 2.4 Backend Scripts Used
* `backend/profiler.py` (Core statistical engine)

### 2.5 Interpretation of Output
A high Quality Score (>90%) indicates clean data requiring minimal LLM intervention. A low score triggers aggressive AI imputation, strict deduplication, and extensive NLP normalization.

---

## 3. Database Studio (Live Database Mode)

### [Add Image Here: Database Connection and Main UI]

### 3.1 Overview
The Database Studio bypasses file uploads entirely, allowing enterprise users to connect directly to live relational databases (MySQL, PostgreSQL, Oracle, SQLite, SQL Server) to perform in-place profiling, querying, and cleaning.

### 3.2 Purpose
* Securely authenticate and connect to live databases.
* Map database schemas, tables, and column metadata.
* Provide a Natural Language Query interface (AI Query Studio).
* Run the Health Profiler against live SQL tables.
* Execute the 12-phase cleaning pipeline with safe transaction write-backs.

### 3.3 UI Components
| Component | Description |
| :--- | :--- |
| **Connection Form** | Input fields for Host, Port, Username, Password, and Database Name. |
| **Database Map** | A dropdown selector to choose the target table for cleaning. |
| **AI Query Studio** | A chat-like interface to query the database using plain English. |
| **Health Profiler Tab** | Displays nulls/duplicates for the selected live table. |
| **Cleaning Studio Tab** | Initiates the AI Pipeline against the live data. |
| **Audit Log Tab** | Displays historical merges and database transactions. |

### 3.4 Internal Working
1. User enters credentials; `DatabaseConnector` establishes an SQLAlchemy engine.
2. Connection states are securely cached via `backend/state_manager.py`.
3. Table metadata (foreign keys, row counts) is fetched.
4. When the user requests a cleaning run, the table is pulled into memory as a dataframe, pushed through the pipeline, and safely written back using a SQL transaction block with `FOREIGN_KEY_CHECKS=0` (if MySQL) to prevent constraint errors.

### 3.5 Backend Scripts Used
* `pages/Live_Database.py` (Frontend UI)
* `backend/db_connector.py` (Database abstraction layer)
* `backend/state_manager.py` (Session persistence)

---

## 4. AI Query Studio

### [Add Image Here: AI Query Studio Chat Interface]

### 4.1 Overview
Embedded within the Database Studio, the AI Query Studio bridges the gap between non-technical users and SQL syntax. It translates conversational prompts into executable, optimized SQL.

### 4.2 Purpose
* Allow users to query live databases using natural language.
* Safely execute `SELECT` (Read) queries instantly.
* Prevent destructive queries (`DELETE`/`DROP`) without explicit manual confirmation.
* Enable follow-up contextual questions.

### 4.3 Internal Working
1. User types query: *"Find missing email addresses."*
2. `NLQueryAgent` receives the prompt alongside the schema metadata.
3. The LLM generates a JSON payload containing the SQL string and an explanation.
4. The system parses the SQL. If it detects Read-intent, it executes via `DatabaseConnector` and renders the output DataFrame.
5. If it detects Write-intent, it triggers an alert asking for user authorization.

### 4.4 Backend Scripts Used
* `agents/nl_query_agent.py`
* `agents/llm_client.py`

---

## 5. AI Cleaning Pipeline (The 12 Stages)

### [Add Image Here: Live Pipeline Logs and Progress Bars]

### 5.1 Overview
The 12-phase pipeline is the core engine of IntelliClean AI. It combines deterministic logic with non-deterministic LLM intelligence to systematically clean, normalize, and deduplicate data.

### 5.2 The 12 Stages Explained

#### Phase 1: Loading & Profiling
* **Action:** The dataframe is loaded, initial memory optimization occurs, and the `DatasetProfiler` computes the baseline health score.

#### Phase 2: AI Schema Analysis
* **Action:** `SchemaAgent` feeds column names and 5 sample rows to the LLM. The LLM classifies the columns (e.g., "Email", "Phone", "Categorical", "Name") so downstream algorithms know how to treat them.

#### Phase 3: Strategy Planning
* **Action:** `PlannerAgent` reviews the schema and profiler report to decide which modules to skip or enforce.

#### Phase 4: String Pre-cleaning & OCR Correction
* **Action:** Lowercases text, strips excess whitespace, and uses heuristics/LLMs to fix OCR mapping errors (e.g., replacing a lowercase `l` in an ID with a `1`).

#### Phase 5: Translation & Transliteration
* **Action:** Scans text columns for non-Latin characters. It translates categorical words to English and *transliterates* proper nouns (e.g., Hindi names to English characters) using LLM batch processing.

#### Phase 6: Entity Resolution
* **Action:** Identifies clusters of strings that represent the same real-world entity despite typos (e.g., "Walmart Inc." vs "Wal-Mart").

#### Phase 7: Domain-Specific Rules
* **Action:** Applies strict RegEx to validate and format emails, phone numbers, and URLs based on the detected column schema.

#### Phase 8: Deduplication & Data Backfill
* **Action:** A massive 6-pass deduplication engine. 
  * Pass 1: Exact Match.
  * Pass 2: Composite Keys (Name + Phone).
  * Pass 3: Fuzzy Matching (Levenshtein distance).
  * *Crucial Step:* Before a duplicate row is deleted, any missing data in the master record (e.g., a blank email) is "backfilled" by copying the email from the duplicate row being deleted.

#### Phase 9: Smart Imputation
* **Action:** Fills remaining null values. Numeric fields use Mean/Median. Categorical fields use Mode or are sent to the LLM to contextually guess the value based on other columns in the row.

#### Phase 10: Outlier Detection
* **Action:** Uses Z-Scores or IQR to identify statistically anomalous numeric values.

#### Phase 11: Validation
* **Action:** `ValidationAgent` runs a spot-check on the cleaned data to ensure no destruction of critical keys occurred, generating a final confidence score.

#### Phase 12: Audit Trail Generation
* **Action:** Compiles all logs, translation dictionaries, and merge clusters into a final JSON metadata object.

### 5.3 Backend Scripts Used
* `backend/pipeline.py` (The Orchestrator)
* `cleaning/deduplication.py`
* `cleaning/imputation.py`
* `cleaning/multilingual.py`
* `cleaning/string_cleaner.py`

---

## 6. Audit Trail & Final Outputs

### [Add Image Here: Audit Log Dashboard showing Deduplication Clusters]
### [Add Image Here: Final Cleaned Dataset Preview]

### 6.1 Overview
IntelliClean AI guarantees 100% transparency. The Audit Log ensures that data engineers can trace exactly *why* a cell was modified or a row was deleted.

### 6.2 Key Features
* **Cluster Merge Maps:** Displays a visual log of which IDs were merged into a single master record during deduplication.
* **Translation Dictionaries:** Shows the exact before-and-after string mappings applied during Phase 5 (Multilingual Processing).
* **Imputation Reasoning:** Displays the logic (Mode, LLM Inference) used to fill specific blank cells.
* **Export Options:** Users can download the cleaned dataset as `.csv` or `.xlsx`, and download the entire Audit Trail as a `.json` file for compliance reporting.

### 6.3 User Workflow
Review Before/After Data Grid &rarr; Review Merge Maps &rarr; Export Cleaned Data to local disk (or commit directly to the Database if in Live Mode).
