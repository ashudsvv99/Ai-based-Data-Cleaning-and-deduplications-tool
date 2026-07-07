# IntelliClean AI: Automated Data Cleaning & Deduplication

[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/ashudsvv99/Ai-based-Data-Cleaning-and-deduplications-tool)

Welcome to **IntelliClean AI**, a state-of-the-art framework designed to solve complex data inconsistency challenges in enterprise datasets. 

Whether you are working with **Offline CSV & Excel files** or connecting directly to **Live SQL Databases**, IntelliClean AI leverages local Large Language Models (LLMs) and advanced mathematical algorithms to clean, normalize, and deduplicate datasets seamlessly—all while operating completely offline to ensure **100% data privacy.**

---

## 🛑 The Core Problem We Are Solving

In the modern enterprise, data is the most valuable asset. However, raw data exported from CRMs, web scraping tools, or legacy databases is almost always messy, unstructured, and plagued with inconsistencies. 

Traditional data cleaning tools and Python scripts fail because they lack "context." For example, a traditional script might blindly translate a French person's name into English, destroying the data. Or, it might fail to realize that `Jon Smith` and `John Smith` are the exact same person because of a simple typo. 

**IntelliClean AI solves this by introducing cognitive, context-aware artificial intelligence into the data pipeline.**

Here is how IntelliClean actively solves the most complex data engineering challenges:

### A. Missing Values (Smart Imputations)
Standard scripts simply fill missing numbers with `0` and missing text with `"Unknown"`. This destroys financial models and statistical integrity.
* **The Solution**: IntelliClean uses contextual **Smart Imputation**. 
* **Example**: If `Delivery_Date` is missing, the AI can dynamically deduce it by writing a rule like `Order_Date + 4 days`. If no rule applies, it mathematically analyzes the column's *skewness*: filling highly distorted salary data with the **Median**, and filling normal data with the **Mean**.

### B. Outlier Detection and Cleaning
Standard scripts usually `drop` rows containing extreme outliers, which permanently destroys all the valid secondary data in that row (like the person's Name and Email).
* **The Solution**: IntelliClean uses the **Interquartile Range (IQR)** to mathematically establish upper and lower bounds.
* **Example**: If a user accidentally types an employee's age as `9999`, the system detects it as an anomaly. Instead of deleting the row, it uses **Winsorization (Clipping)** to gently reduce the `9999` back down to the 95th percentile limit (e.g., `85`), perfectly preserving the row's integrity.

### C. Duplicate Values (Exact, Partial, Fuzzy, and Semantic)
Standard scripts use `df.drop_duplicates()`, which only catches 100% identical byte-for-byte rows.
* **The Solution**: IntelliClean resolves four distinct types of duplicates using $O(N)$ Sorted Neighbourhood Indexing and RapidFuzz scoring:
  1. **Exact**: Entire rows that match perfectly.
  2. **Partial**: Rows differing in only a few empty fields.
  3. **Fuzzy**: Typo variations (e.g., resolving `Sameep` vs `Samip`). *Note: The system temporarily drops exact identifier columns like `transaction_id` during fuzzy matching to prevent accidentally merging valid, unique financial transactions.*
  4. **Semantic**: Resolving meaning variations (e.g., mapping `IBM` to `International Business Machines`).

### D. Multilingual Translations and Transliterations (Entity Preservation)
Traditional translation APIs blindly translate everything. If a person's name is "Rose", a blind translator might turn it into the Spanish word "Rosa", altering their legal identity.
* **The Solution**: IntelliClean features strict **Entity Preservation**. 
* **Example (Transliteration)**: The system knows *never* to translate Entities (Names, Addresses). Instead, it uses phonetic **Transliteration**. If it sees the Hindi name `समीप`, it transliterates it to the ASCII equivalent `Sameep`. This allows the Deduplication engine to instantly recognize that `समीप` and `Sameep` are cross-language duplicates of the exact same person!
* **Example (Translation)**: It reserves true *translation* purely for Free Text columns, using $O(1)$ Token Caching to batch-translate foreign reviews into English (e.g., "München is great" -> "Munich is great").

---

## 📈 Real-World Benefits (Why Use This?)

How is IntelliClean AI helpful for your business?

### Key Benefits
*   **Massive Time Savings**: Automates hundreds of hours of manual Excel cleaning, Python scripting, and regex writing. What takes a data engineer days can be accomplished in minutes.
*   **Zero Data Leakage (Enterprise Privacy)**: By using highly optimized Local LLMs (via LM Studio), 100% of the data stays on your machine. This is crucial for healthcare (HIPAA), finance, and enterprise compliance.
*   **High Confidence and Transparency**: No more black-box AI. The Explainability Module ensures that every single cell modification is logged with a human-readable reason and confidence score.
*   **Hardware Efficiency**: Designed specifically to run on standard corporate laptops (like an i3 processor with 12GB RAM) without crashing, thanks to PyArrow ingestion, aggressive downcasting, and algorithmic blocking.

### Primary Use Cases
*   **CRM & Lead Deduplication**: Merging sales leads from multiple sources (e.g., Salesforce, HubSpot) where names are misspelled, phone numbers have different formats, and emails contain typos.
*   **E-Commerce Catalog Standardization**: Normalizing product descriptions, handling missing prices, and translating foreign language reviews into English.
*   **Healthcare Patient Records**: Consolidating patient records securely offline, merging variations of addresses and names without losing secondary medical history.
*   **Financial Data Consolidation**: Converting mixed currencies to a standard format (e.g., INR) and securely cleaning transaction logs directly from live databases using the built-in Natural Language Query Console.

---

## 📂 Supported Data Sources (How We Ingest Data)

IntelliClean AI is highly flexible and currently implements two primary data ingestion methods:

### A. Offline File Cleaning (CSV & Excel)
* **The Process**: Simply drag and drop `.csv`, `.xls`, or `.xlsx` files into the Streamlit UI. 
* **The Logic**: The system uses the **PyArrow C++ engine** to rapidly ingest files up to 200MB instantly, automatically catching and fixing broken encoding and standardizing blank cells.

### B. Live Database Connection & Cleaning
* **The Process**: Input your credentials to connect directly to live infrastructure (PostgreSQL, MySQL, SQL Server, Oracle, SQLite, DB2).
* **The Logic**: The system uses `sqlalchemy` to establish a secure connection pool. To prevent massive databases from crashing your local machine, the system automatically pulls a **100,000-row sample** to run the cleaning pipeline on.
* **NL Query Console**: Non-technical stakeholders can type questions in plain English (e.g., *"Show me the top 5 duplicate transactions"*), and the AI will safely generate and execute the SQL `SELECT` query in real-time.

---

## ⚙️ The 12-Step AI Cleaning Workflow (How It Works)

Curious how the magic happens? Here is a human-friendly breakdown of the logic implemented inside every core script:

1. **Ingestion (`loader.py`)**: Reads the data safely and standardizes all blank spaces.
2. **Fast Schema Detection (`schema_detector.py`)**: A lightning-fast heuristic filter that uses simple regex to instantly identify obvious columns like Emails, URLs, Dates, and Currencies.
3. **AI Schema Guessing (`schema_agent.py`)**: For complex columns, the local LLM evaluates a sample of the data and categorizes it logically (e.g., "This is an Entity Name" vs "This is Free Text").
4. **Industry Context (`domain_profiler.py`)**: The AI guesses the industry (e.g., "Healthcare") to adjust how it cleans later on.
5. **Aggressive Scrubbing (`quality_filter.py`)**: Drops totally useless columns (90% empty) and blank rows.
6. **Mixed Type Fixing (`datatype_cleaner.py`)**: If a column contains both text and numbers, it forces it into a single, clean mathematical format.
7. **Text & Syntax Formatting (`string_cleaner.py`, `standardizer.py`)**: Removes invisible characters and trailing spaces that corrupt data.
8. **Currency & Translation (`currency_converter.py`, `multilingual.py`)**: Standardizes global currencies to a baseline (₹) and batch-translates foreign reviews to English.
9. **Fuzzy Deduplication (`deduplication.py`)**: Uses "Sorted Neighbourhood Indexing" to alphabetize data, bringing typos (`Sameep` and `Samip`) next to each other. It then mathematically calculates their similarity to catch phonetic misspellings in seconds.
10. **Entity Merging (`entity_resolution.py`)**: Merges the found duplicates into a single "Golden Record", taking the best information from all rows so nothing is lost.
11. **Smart Imputation & Outliers (`missing_values.py`, `outliers.py`)**: Writes dynamic AI rules (e.g., "Delivery Date = Order Date + 4 days") to fill blanks. Clips extreme numeric anomalies gently using IQR boundaries.
12. **Final Export (`explanation_agent.py`)**: Translates all the technical metadata into a beautiful, human-readable Markdown report and exports your pristine CSV.

---

## 🛠️ Technology Stack & Memory Optimization

*   **Frontend**: `streamlit` (Real-time UI rendering with raw HTML/CSS glassmorphism aesthetics).
*   **Data Engineering**: `pandas`, `pyarrow` (High-speed C++ ingestion), `numpy`.
*   **Matching & Deduplication**: `recordlinkage` (Sorted Neighbourhood Indexing), `rapidfuzz` (Levenshtein distance).
*   **String Processing**: `unidecode`, Python `re`.
*   **AI Integration**: `requests` (Local REST API via LM Studio), `pydantic`.
*   **Database & System**: `sqlalchemy`, database drivers (`psycopg2-binary`, `pymysql`, `pyodbc`, `oracledb`, `ibm_db_sa`), `psutil` (system monitoring), `tabulate`.

---

## 🚀 Complete Setup & Installation Guide

### 1. System Prerequisites
*   Ensure you have **Python 3.10 or higher** installed. Verify via terminal: `python --version`.
*   Ensure you have sufficient RAM (minimum 12GB recommended).

### 2. Clone the Repository
Open a terminal and clone the repository to your local machine:
```bash
git clone https://github.com/ashudsvv99/Ai-based-Data-Cleaning-and-deduplications-tool.git
cd "Ai based Automated Data cleaning and Deduplication"
```

### 3. Create a Virtual Environment (Highly Recommended)
*   **Windows**:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```
*   **Mac/Linux**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

### 4. Install Dependencies
Install all required packages from the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### 5. Set Up Local AI Engine (LM Studio)
IntelliClean relies on a local LLM to perform cognitive evaluations without exposing your data to the cloud.
1. Download and install [LM Studio](https://lmstudio.ai/).
2. Search for a lightweight Instruct model (e.g., **Qwen**, **DeepSeek-R1**, or **Llama 3 8B** in **GGUF Q4_K_M** format).
3. Navigate to the **Local Inference Server** tab and click **Start Server** (`http://localhost:1234/v1`).

---

## 💡 Quick Start Guide

1. Start the server from the root directory:
```bash
streamlit run app.py
```
2. A browser window will automatically open pointing to `http://localhost:8501`.
3. Upload your dirty dataset (`.csv` or `.xlsx`) or navigate to the `Live_Database` page on the sidebar.
4. Watch the "Pipeline Logs" to see the AI's "thought process" in real-time.
5. Review the **Data Quality**, **Imputations**, and **Audit Trail** dashboards, then download your final Cleaned Dataset!

*For a much deeper, developer-focused dive into the architecture, please read [COMPLETE_DOCUMENTATION.md](COMPLETE_DOCUMENTATION.md).*
