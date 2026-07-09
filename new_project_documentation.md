# IntelliClean AI: Automated Data Cleaning and Deduplication Tool
## Complete Project Documentation

**IntelliClean AI** is an advanced, LLM-powered data cleaning and deduplication pipeline. It tackles messy, unstructured, and duplicated records by leveraging artificial intelligence to infer schemas, transliterate foreign languages, correct OCR errors, smartly impute missing values, and perform fuzzy deduplication.

This document showcases the full application flow, broken down into its two primary operating modes: **CSV/Excel File Cleaning** and **Live Database Cleaning**.

---

## 1. Global Configurations
Before running the pipeline, the system allows the user to configure the underlying LLM models and core application settings directly from the UI. This provides immense flexibility for deploying locally or in the cloud.

**Features:**
- **Model Selection:** Choose between lightweight local models (e.g., Llama 3) or heavy-duty cloud endpoints.
- **Agent Parameters:** Adjust temperature and context windows for the Schema, Planning, and Deduplication agents.
- **Pipeline Toggles:** Enable or disable specific phases like Multilingual translation or Currency normalization depending on the dataset.

![Global Config](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/Globalconfig.png)

---

## 2. Mode 1: CSV and Excel Based Cleaning
This module is designed for flat-file ingestion. Users can upload messy CSV or Excel datasets, profile them, and run them through the AI pipeline.

### 2.1. Main Dashboard & Data Ingestion
The homepage features a sleek, drag-and-drop interface for data uploading. The application supports large `.csv` and `.xlsx` files and loads them instantly into a pandas DataFrame.

**Features:**
- Real-time preview of the first 100 rows.
- Instant metadata extraction (total rows, columns, memory usage).
- Secure, browser-side file parsing.

![Main App Dashboard](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/app1.png)
![Data Ingestion](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/1%20Data%20Ingestion.png)

### 2.2. Health Profiler & Statistics
Once the data is loaded, the intelligent profiler scans the dataset to generate an initial data health score. 

**Features:**
- **Quality Score:** A percentage metric indicating how "dirty" the data is before cleaning.
- **Missing Values Analysis:** Shows exactly which columns have nulls and what percentage of the dataset is incomplete.
- **Duplicate Detection:** Identifies *exact* row duplicates immediately.
- **Statistical Summary:** Computes means, medians, standard deviations, and unique value counts for numeric and categorical columns.

![View Datasets and Statistics](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/2%20View%20Datsets%20and%20Statistics.png)
![Statistical Summary](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/2%20Statistical%20Summary.png)
![Missing Values Report](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/2%20Missings%20values.png)

### 2.3. AI Cleaning Pipeline Execution
With one click, the 12-phase AI pipeline is triggered. The UI displays real-time execution logs as the LLM processes the data step-by-step.

**Key Phases Demonstrated:**
- **Schema Analysis:** The LLM scans column headers and sample data to determine the semantic intent (e.g., classifying a column as "Name", "Email", or "Location").
- **Multilingual Detection & Transliteration:** The pipeline detects non-Latin scripts (like Hindi/Devanagari) and automatically transliterates names and translates categories into English for uniform processing.
- **Currency Normalization:** Detects mixed currency symbols ($, €, ₹) and standardizes them into a single numeric base currency.

![Pipeline Execution](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/3%20Pipeline%20Executions.png)
![Schema Analysis Phase](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/6%20Schema%20Analysis.png)
![Multilingual Detection](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/7%20Multilingual%20detection.png)
![Currency Normalization 1](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/13%20Currency.png)
![Currency Normalization 2](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/13.png)

### 2.4. Smart Imputation & Deduplication
The pipeline performs advanced entity resolution and infers missing values.

**Features:**
- **Smart Deduplication (Entity Resolution):** Uses composite keys and fuzzy string matching (Levenshtein distance) to identify rows that belong to the same real-world entity, even if there are typos (e.g., "John Doe" vs "Jhohn Doe").
- **Backfill Imputation:** Before deleting a duplicate row, the system extracts any missing information (like a missing phone number) and copies it to the master record.
- **Statistical Imputation:** Uses Mode, Mean, or LLM-inference to fill remaining blanks intelligently.

![Smart Imputation](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/8%20Smart%20Imputation.png)
![Deduplication Results](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/9%20Deduplication.png)

### 2.5. Final Cleaned Data & Audit Trail
The system outputs the cleaned dataset and a comprehensive audit trail of all inferences made. Users can download the final CSV.

![Cleaned Data Preview 1](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/4%20Cleaned%20Data.png)
![Cleaned Data Preview 2](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/5%20Cleaned%20Data.png)
![Audit Trail](file:///C:/Users/ak656/Desktop/project%20documentations/Excel-Csv%20Cleaning/14%20Audit%20Trail.png)

---

## 3. Mode 2: Live Database Cleaning
This module integrates directly with production databases (MySQL, PostgreSQL, etc.), allowing users to clean live tables, run automated pipelines, and execute natural language SQL queries without touching code.

### 3.1. Database Connection & Setup
Users can securely connect to local or remote database instances. The system caches credentials across page reloads to ensure a seamless experience.

**Features:**
- Support for multiple engines (MySQL, Postgres, SQLite, etc.).
- Dropdowns to select the Database and Table.
- Connection testing and error handling.

![DB Connection 1](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/1.png)
![DB Connection 2](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/2.png)
![DB Connection 3](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/3.png)
![DB Connection 4](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/4.png)

### 3.2. Live Database Health Profiler
Similar to the CSV mode, this profiler scans the selected live table directly via SQL queries to gather metadata without pulling the entire database into memory.

![Live Health Profiler 1](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/6%20Health_profiler.png)
![Live Health Profiler 2](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/7%20Health%20Profiler.png)
![Live Health Profiler 3](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/8%20Health%20Profiler.png)

### 3.3. AI Query Studio
The **AI Query Studio** allows non-technical users to chat with their live database using natural language. 

**Features:**
- **NL to SQL:** The LLM translates prompts like "Find missing emails" into optimized MySQL syntax.
- **Safety First:** Destructive queries (DELETE/DROP) are caught, and the system prompts for explicit confirmation.
- **Auto-Execution:** Read queries are executed automatically, and results are displayed in a clean DataFrame grid.

![AI Query Studio](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/9%20Ai%20Queries%20studio.png)

### 3.4. Live Database AI Cleaning Studio
Users can launch the 12-phase automated pipeline directly against the database table. The system safely pulls the data, processes it, and manages transactions and foreign-key locks during write-backs.

![Cleaning Studio Launch 1](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/12%20AI%20Cleaning%20Studio.png)
![Cleaning Studio Launch 2](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/13%20AI%20Cleaning%20Studio.png)

### 3.5. Live Data AI Processing Steps
The agent identifies schemas, translates fields, and deduplicates directly on the database records just like the CSV pipeline, but optimized for relational data constraints.

![Schema Analysis](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/15%20Schema%20Analysis.png)
![Multilingual Detection](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/16%20Multi-lingual%20detection.png)
![Imputation Strategies](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/17%20imputations.png)
![Live Deduplication](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/18%20deduplication.png)

### 3.6. Final Results & Database Audit Logs
After cleaning, the system pushes the data back to the live database (handling Foreign Keys automatically) and presents a deeply detailed Audit Log.

**Features:**
- View the finalized cleaned table before committing.
- **Deduplication Cluster Map:** A visual log showing exactly which IDs were merged and why.
- **LLM Reasoning Logs:** Expandable JSON metadata tracking the rationale behind every modification, imputation, and translation made during the pipeline run.

![Cleaned Live Data](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/14%20Cleaned%20Data.png)
![Audit Log Preview 1](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/10%20Audit%20log.png)
![Audit Log Preview 2](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/11%20Audit%20log.png)
![Comprehensive Audit Trails](file:///C:/Users/ak656/Desktop/project%20documentations/Live%20DB%20cleaning/19%20Audit%20trails.png)

---
*Generated by IntelliClean AI Documentation Engine.*
