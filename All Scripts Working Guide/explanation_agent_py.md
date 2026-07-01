# `agents/explanation_agent.py` - The Technical Translator

The `metadata` dictionary tracks thousands of data points: exact rows dropped, fuzzy match threshold percentages, skewness coefficients, and IQR bounds. This is completely unreadable for a non-technical business analyst. The `ExplanationAgent` translates this raw JSON telemetry into a professional, human-readable executive summary.

## Full Working Process & Logic

### 1. Payload Optimization (Trimming the Fat)
- **Problem**: The `metadata` dictionary contains raw data lists (like lists of dropped test emails or sample validation rows). Sending this massive dictionary to the LLM will exceed its Context Window (Token Limit).
- **Solution**: The script runs a preprocessing loop. It copies the `metadata` dictionary and actively deletes large, token-heavy fields:
  - `compact_meta.pop("schema_mapping", None)`
  - `compact_meta.pop("validation_issues", None)` (If they are too long).
- **Why**: The LLM only needs the *statistics* (e.g., "Dropped 5 rows", "Score increased by 20%"), not the raw data itself, to write a summary report.

### 2. Markdown Generation
- **Prompting**: The LLM is instructed to act as a Data Engineering Consultant. It must write a structured report using Markdown (`#`, `##`, `- bullet points`).
- It is instructed to highlight the Delta ($\Delta$): The difference between the `quality_score_before` and `quality_score_after`.
- It is instructed to explain *why* decisions were made (e.g., "We clipped outliers using IQR to preserve row integrity").

### 3. Handoff to Exporter
- The resulting string is purely text. The script returns this Markdown string back to the `PipelineOrchestrator`, which passes it to `exporter.py` to be saved as `reports/cleaning_report.md`.
