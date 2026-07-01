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
