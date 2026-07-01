# `backend/profiler.py` - The Statistical Baseline Calculator

Before we alter a single byte of data, we need a mathematical baseline. The `DataProfiler` calculates raw statistical metrics (Missing Percentages, Duplicate Counts) and computes an overall "Quality Score" out of 100.

## Full Working Process & Logic

### 1. Missing Value Auditing
- **Method**: `_calculate_missing()`
- **Logic**: It creates a boolean mask of the entire dataset using `df.isna()`. It calls `.sum()` to count the exact number of `pd.NA` cells.
- It calculates `missing_pct = (total_missing / (total_rows * total_columns)) * 100`. 
- **Why**: By getting the percentage of missing data across the entire matrix (not just row-by-row), we get a global perspective of data sparseness.

### 2. Exact Duplicate Auditing
- **Method**: `_calculate_duplicates()`
- **Logic**: It uses Pandas vectorization `df.duplicated(keep='first').sum()`. 
- **Why**: This does *not* do fuzzy matching. It mathematically hashes every row and compares it. If two rows are exact bit-for-bit copies of each other, it counts them.

### 3. The Quality Score Formula
- **Logic**: `score = 100.0 - (missing_pct * 1.5) - (duplicate_pct * 2.0)`
- **Why these weights?**: The formula penalizes exact duplicates slightly harder (`2.0` multiplier) than missing values (`1.5` multiplier). Why? Because a missing value is just incomplete data, but a duplicate row actively distorts financial metrics (e.g., doubling revenue by accident). The final score is clipped `max(0, min(100, score))` to ensure it always renders beautifully in the UI between 0 and 100.
