# `cleaning/datatype_cleaner.py`

## Overview
`datatype_cleaner.py` is an aggressive scrubbing phase script executed early in the pipeline. It is responsible for fixing corrupted data types, normalizing booleans, and resolving "mixed-type" columns (columns that accidentally contain both strings and numbers).

## Logic and Architecture

### 1. Mixed-Type Resolution
Pandas struggles significantly when a column has a dtype of `object` but actually contains a mixture of integers, floats, and strings.
- **Action**: The cleaner samples the column. If it finds that >60% of the column can be safely converted to a numeric type (using `pd.to_numeric(errors='coerce')`), it forcefully converts the entire column to numeric. Any string values that fail to convert (like `"N/A"` or `"Unknown"`) are converted to `NaN`, which the pipeline's imputation engine will handle later.
- **Benefit**: Prevents downstream crashes in outlier detection and mathematical validation functions.

### 2. Boolean Mapping
Often, boolean columns are represented ambiguously (e.g., `"Yes"/"No"`, `"Y"/"N"`, `"True"/"False"`, `1/0`).
- **Action**: It detects low-cardinality columns that strictly match boolean intent and maps them explicitly to standard Python `True`/`False` booleans.

### 3. Date Parsing
- **Action**: It aggressively hunts for columns with date-like names (e.g., `dob`, `order_date`) or date-like string formats. When found, it coerces them to standard `datetime64[ns]` formats.
