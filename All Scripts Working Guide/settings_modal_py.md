# `components/settings_modal.py` - The Global Configuration Panel

To provide a premium experience, parameters such as matching thresholds and LLM server routes should be configurable via a dynamic overlay dialog instead of standard sidebar widgets.

## Full Working Process & Logic

### 1. Overlay Dialog Integration
- **Logic**: Integrates Streamlit's modal overlay framework via `st.dialog` or `st.experimental_dialog`.
- **Action**: Renders a configuration form containing slider inputs for temperature, fuzzy thresholds, batch chunk sizes, and outlier bounds.
- **Saving Configurations**: Validates form inputs, maps them to settings, updates `config.py` in-place using `update_config_file`, and triggers a page rerun using `st.rerun()` to load the modified settings.
