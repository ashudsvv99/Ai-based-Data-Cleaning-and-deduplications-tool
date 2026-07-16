# Project Structure

Below is the current directory and file structure of the AI Automated Data Cleaning and Deduplication platform. 

```text
/
├── app.py                     # Main application entry point
├── requirements.txt           # Python dependencies
├── README.md                  # Project overview
├── Project_REQUIREMENTS.md    # Initial requirements document
├── Project Explainations.md   # Explanation of project modules
├── realistic_data_quality_issues.sql  # SQL schema/seed data
│
├── agents/                    # AI Agent Logic
│   ├── llm_client.py
│   ├── nl_query_agent.py
│   └── planner_agent.py
│
├── backend/                   # Database Interactions
│   └── db_connector.py
│
├── cleaning/                  # Core Data Processing Logic
│   ├── core.py
│   ├── deduplication.py
│   ├── imputation.py
│   ├── outliers.py
│   └── type_casting.py
│
├── components/                # Modular Streamlit UI Components
│   ├── data_health_ui.py
│   ├── settings_modal.py
│   ├── system_monitor.py
│   └── ui_components.py
│
├── pages/                     # Streamlit App Pages (Sidebar navigation)
│   ├── AI_Query_Studio.py
│   ├── Database_Management.py
│   ├── Data_Cleaning_Agent.py
│   ├── Live_Database.py
│   └── Overview.py
│
├── exports/                   # Cleaned data CSV exports
├── logs/                      # System operation logs
├── reports/                   # Markdown cleaning execution reports
└── Sample datasets/           # Assorted CSVs for testing and simulation
```
