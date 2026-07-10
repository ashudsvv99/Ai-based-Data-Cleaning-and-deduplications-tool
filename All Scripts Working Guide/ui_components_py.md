# `components/ui_components.py` - The Visual Renderer & Dashboard Manager

To separate logic from user interface presentation, all advanced styling and interactive dashboard rendering are isolated in `ui_components.py`.

## Full Working Process & Logic

### 1. Glassmorphism Design & CSS Panels
- **Logic**: Embeds custom HTML/CSS sheets within Streamlit layouts to render premium card grids and metrics.
- **Tab Panel Layouts**: Generates visual tab interfaces (Cleaned Data, Schema Analysis, Multilingual, Imputation, Deduplication, Currency, and Audit Trail).
- **Audit Trails**: Renders before/after comparisons, deduplication merge lists showing clustered duplicates, translation dictionaries, and custom file download triggers for CSV, Excel, and JSON files.
