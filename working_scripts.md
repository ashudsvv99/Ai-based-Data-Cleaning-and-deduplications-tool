# Working Scripts Reference

Below is a detailed breakdown of all the active working scripts in the AI Automated Data Cleaning and Deduplication platform and what responsibilities they hold.

## 1. Core Application
- **`app.py`**: The main entry point for the Streamlit application. It configures the global page settings, imports the global CSS (dark mode, glassmorphism UI), initializes session state variables, and orchestrates navigation across the different application pages.

## 2. Streamlit Pages (`/pages`)
- **`Overview.py`**: Displays the master dashboard. It connects to the SQLite database to pull system-wide metrics (Total Rows, Deduplicated Records, Memory footprint), renders the "Data Health Profile" (cleanliness score, distribution charts, anomaly gauges), and showcases recent platform activity logs.
- **`Data_Cleaning_Agent.py`**: The core execution interface. It provides the UI for selecting a target table and firing off the AI Data Cleaning Pipeline. This is where users see the loading states, transformation logs, and the final Data Health before/after metrics.
- **`AI_Query_Studio.py`**: A natural language chat interface. It uses the `nl_query_agent` to translate English questions into SQL, runs the SQL against the active database, and returns formatted dataframes and insights.
- **`Live_Database.py`**: A highly interactive schema explorer. It uses `streamlit-agraph` to render an interactive node-based Knowledge Graph of the database tables and columns. It also houses the **AI Audit Log** tab, which displays full-window detailed reports of every action and query run on the platform.
- **`Database_Management.py`**: A utility page for connecting to databases, viewing raw table schemas, ingesting CSV files, dropping tables, and maintaining the raw data repository.

## 3. UI Components (`/components`)
- **`ui_components.py`**: Houses reusable UI functions. It includes the `render_cleaning_results()` function which displays the "AI Audit Trail" (the step-by-step changes made to the data) and the full Execution Log dialogs.
- **`data_health_ui.py`**: Contains the logic and layout rules for rendering the Data Health Profile metric cards, progress bars, and Plotly charts (gauges, donuts). It uses CSS Grid to ensure perfect alignment.
- **`system_monitor.py`**: A background utility that reads live OS metrics (CPU usage, Memory consumption, Disk usage) and renders a floating status bar in the UI, updating continuously.
- **`settings_modal.py`**: Provides a settings interface for configuring LLM endpoints (like Gemini, OpenAI, or local models) and tweaking system parameters.

## 4. AI Agents (`/agents`)
- **`llm_client.py`**: The unified abstraction layer for interacting with LLM APIs. It handles API keys, constructs prompts, sends requests to the language model, and parses the JSON responses securely.
- **`nl_query_agent.py`**: A specialized agent that understands database schemas. It receives natural language requests (e.g., "Show me top 5 users by revenue"), queries the schema, generates a valid SQL statement, and formats the output.
- **`planner_agent.py`**: A high-level orchestration agent. It determines the optimal sequence of cleaning tasks (e.g., whether imputation should happen before deduplication) based on a high-level scan of the dataset.

## 5. Data Cleaning Engine (`/cleaning`)
- **`core.py`**: The heart of the cleaning pipeline. It invokes the other modules sequentially (Type Casting -> Imputation -> Outliers -> Deduplication). It applies the transformations directly to the Pandas DataFrame and builds a comprehensive metadata trail.
- **`deduplication.py`**: Detects and handles duplicate records. It employs two methodologies:
  - **Type 1 (Exact Match)**: Standard hashing and grouping of identical rows.
  - **Type 2 (Fuzzy Match)**: Uses algorithms (like Levenshtein distance or TF-IDF) to find records that are highly similar but not exactly identical (e.g., "Jon Doe" vs "John Doe").
- **`imputation.py`**: Scans for `NULL` or missing values. Depending on the column type (categorical vs numerical) and AI hints, it fills the missing data using mean/median interpolation or frequent categories.
- **`outliers.py`**: Uses statistical methods (like Z-score or IQR) to identify data points that deviate wildly from the norm, flagging them or clipping them as configured.
- **`type_casting.py`**: Automatically coerces columns into their optimal data types (e.g., turning a string column filled with dates into actual `datetime` objects, or strings to integers) to optimize memory and enable proper analysis.

## 6. Backend Integration (`/backend`)
- **`db_connector.py`**: The singleton class responsible for interfacing with the SQLite database (or extending to PostgreSQL/MySQL). It provides secure methods to execute queries, fetch schemas, write dataframes (`to_sql`), and back up tables before destructive cleaning actions.
