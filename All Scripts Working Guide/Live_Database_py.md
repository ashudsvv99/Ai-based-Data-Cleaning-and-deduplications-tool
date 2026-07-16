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


### Recent Problems & Architectural Fixes
- **Problem**: The old UI used standard Streamlit radio buttons, making the navigation feel disjointed and non-premium. Furthermore, the cleaning pipeline wasn't fully integrated with the database sampling.
- **Fix**: Completely overhauled the UI using raw HTML/CSS to inject modern, glassmorphic pill-based tabs. Integrated the full 12-phase `PipelineOrchestrator` directly into the live database viewer, ensuring that the 100k-row memory limit sample is seamlessly passed to the cleaning engine without hanging the database connection.
