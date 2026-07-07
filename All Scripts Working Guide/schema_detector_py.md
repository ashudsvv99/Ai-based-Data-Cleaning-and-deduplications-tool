# `backend/schema_detector.py`

## Overview
`schema_detector.py` is a highly optimized heuristic pre-filter used to infer the semantic category of DataFrame columns *before* relying on the LLM `SchemaAgent`. 

## Logic and Architecture
By using fast regex and string matching to identify obvious column types (e.g., Dates, Emails, URLs, Currencies, Phone numbers), this script saves significant computational time and LLM token usage.

### 1. The Heuristic Filters
The `HeuristicSchemaDetector` tests a small sample (typically 10-20 non-null values) of a column against strict rules:
- **Email**: Uses regex to find `something@something.domain`.
- **URL**: Uses regex to find `http://` or `www.`.
- **Date**: Uses `pd.to_datetime` with `errors='coerce'` to see if >80% of values are valid timestamps.
- **Currency**: Checks for monetary symbols (`$`, `€`, `£`, `₹`) or currency codes (`USD`, `EUR`).
- **Phone**: Checks for dial codes (`+91`, `+1`) or consecutive digits matching phone patterns.
- **Categorical**: If a text column has very few unique values relative to its size (low cardinality), it is flagged as categorical.

### 2. LLM Fallback
If the heuristic filter returns `Unknown` or `Free Text` (because the column is ambiguous, like a 'Name' or 'Address' column), the system will seamlessly pass that specific column to the LLM-based `SchemaAgent` for deeper semantic analysis. This hybrid approach guarantees both speed and accuracy.
