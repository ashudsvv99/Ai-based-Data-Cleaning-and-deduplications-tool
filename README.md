# ✦ IntelliClean AI

IntelliClean AI is a universal, domain-independent data quality framework powered by a local Large Language Model (LLM) and deterministic algorithms. It provides a beautiful, premium glassmorphism Streamlit UI to automate end-to-end data cleaning, handling messy datasets across any industry without sending your sensitive data to the cloud.

---

## 🚀 Key Features

* **AI Schema Detection & Planning:** Uses a local LLM to understand your dataset semantics (e.g., classifying columns as `Email`, `Location`, `Categorical`) and automatically plans the best cleaning strategies.
* **Multilingual Translation & Transliteration:** Automatically detects non-English text (e.g., Hindi, Tamil) and translates categorical values or transliterates human names into English.
* **Smart Contextual Imputation:** The AI writes contextual rules to fill missing values (e.g., "IF B2B THEN Priority = High") and falls back to advanced statistical imputation (mean, median, mode) with rich distribution tracking.
* **Fuzzy Graph Deduplication:** Uses `rapidfuzz` and Union-Find graph algorithms to detect exact and partial/fuzzy duplicates (e.g., `John Doe` vs `Jhon Doe`), intelligently consolidating conflicting data into a single master canonical record.
* **Domain Intelligence:** Automatically detects the industry domain of your dataset (Retail, Healthcare, Finance, etc.) using a hybrid keyword heuristics and AI reasoning approach.
* **Beautiful Dark-Mode UI:** A 14-phase execution pipeline with a premium, real-time interactive dashboard to visualize all AI decisions and dataset transformations.
---
## 🛠️ Tech Stack
* **Frontend:** Streamlit, HTML/CSS (Custom Glassmorphism design)
* **Backend:** Python, Pandas, Numpy
* **Algorithms:** RapidFuzz (fuzzy matching), RecordLinkage (blocking), Union-Find (graphs)
* **AI Engine:** Local LLM (e.g., Google Gemma 2B or Llama 3) running via [LM Studio](https://lmstudio.ai/) (OpenAI-compatible local server).
---
## ⚙️ Setup & Installation
### 1. Prerequisites
* **Python 3.9+** installed on your machine.
* **LM Studio** installed to run the local LLM server.
### 2. Install Dependencies
Clone the project and install the required Python packages:
```bash
# Navigate to the project directory
cd "Ai based Automated Data cleaning and Deduplication"
# (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# Install requirements
pip install -r requirements.txt
```
### 3. Setup Local AI (LM Studio)
Because this app is designed for complete privacy and offline use, it relies on a local LLM.
1. Download and open **LM Studio**.
2. Download a fast, lightweight model (e.g., **Google Gemma 2B Instruct** or **Qwen 2.5 1.5B**).
3. Go to the **Local Server** tab in LM Studio.
4. Ensure the server port is running on `http://127.0.0.1:1234` (the default).
5. Click **Start Server**.
*Note: If your local server is running on a different port, you can update it in the UI sidebar when you run the app.*
---
## 💻 How to Run
Once dependencies are installed and LM Studio is running:
1. Start the Streamlit frontend:
   ```bash
   streamlit run app.py
   ```
2. Your browser should automatically open to `http://localhost:8501`.
3. Drop a `.csv` or `.xlsx` file into the upload zone.
4. Click **Start AI Cleaning Pipeline**.
---
## 🧪 Testing the System
We have included 5 pre-generated "dirty" datasets covering different domains in the `data/` folder. They contain missing values, extreme numeric outliers, exact duplicates, fuzzy duplicates, and mixed multilingual text (like Hindi/English).
* `data/1_retail_dirty.csv`
* `data/2_healthcare_dirty.csv`
* `data/3_finance_dirty.csv`
* `data/4_hr_dirty.csv`
* `data/5_logistics_dirty.csv`
Try uploading them to see how IntelliClean AI handles different schemas and automatically formulates rules to clean them!
---
## 📁 Project Structure
```text
AI_Data_Cleaner/
├── app.py                      # Main Streamlit Frontend
├── config.py                   # Global configurations
├── requirements.txt            # Python dependencies
├── backend/
│   ├── pipeline.py             # Orchestrates the 14-phase cleaning workflow
│   ├── domain_profiler.py      # Detects dataset industry domain
│   ├── profiler.py             # Basic dataset profiling
│   ├── schema_detector.py      # Heuristic column typing
│   └── validator.py            # Final quality validation checks
├── agents/
│   ├── llm_client.py           # Connects to LM Studio / Local AI
│   ├── planner_agent.py        # Generates imputation rules & maps strategies
│   ├── schema_agent.py         # AI verification of column types
│   └── explanation_agent.py    # Generates audit trail explanations
├── cleaning/
│   ├── missing_values.py       # Smart rule & statistical imputation (runs first)
│   ├── outliers.py             # Outlier clipping & domain capping (runs second)
│   ├── deduplication.py        # Fuzzy graph entity consolidation
│   ├── currency_converter.py   # Mixed currency detection & conversion to INR (₹)
│   ├── multilingual.py         # Translation & Transliteration
│   ├── entity_resolution.py    # Merging translated canonical names
│   └── standardizer.py         # Casing & regex standardization
├── data/                       # Contains the generated dirty test datasets
└── reports/                    # Auto-generated markdown audit reports
```
