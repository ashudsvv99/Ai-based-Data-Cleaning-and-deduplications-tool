# `cleaning/quality_filter.py` - Multi-Dimensional Junk Scrubber

Why waste expensive AI tokens and processing power trying to "clean" a row that is entirely blank? The `QualityFilter` class acts as the bouncer of the pipeline, aggressively dropping useless data *before* any cleaning begins.

## Full Working Process & Logic

The `filter_useless_data()` method executes a multi-dimensional scrub using Pandas vectorization for maximum speed.

### 1. Column-Level Sparsity Check
- **Logic**: `col_thresh = int(len(df_clean) * 0.1)`
- **Action**: It calculates a threshold representing 10% of the total rows. It then calls `df_clean.dropna(axis=1, thresh=col_thresh)`.
- **Why**: If a column has 10,000 rows, but 9,500 of them are `pd.NA` (95% missing), that column provides zero statistical value. It drops the entire column permanently.

### 2. Row-Level Sparsity Check
- **Logic**: `threshold = len(df_clean.columns) // 2`
- **Action**: It requires a row to have at least half of its columns filled with valid data to survive (`df.dropna(thresh=threshold)`).
- **Why**: If a row has 30 columns, but 20 of them are blank, it's a corrupted record.

### 3. Critical Identifier Check (Domain Agnostic)
- **Logic**: The script iterates through `df_clean.columns` and cross-references them against a `critical_keywords` list (`["email", "phone", "city", "address", "name"]`). It also checks the `schema_type` mapped by the `SchemaAgent`. 
- **Action**: If it finds multiple critical columns in the dataset, it calculates `min_required = len(critical_cols) - 1`. It then runs `df.dropna(subset=critical_cols, thresh=min_required)`.
- **Why**: If a record is missing BOTH an Email AND a Phone Number, it's completely unrecoverable for business purposes. The LLM shouldn't be asked to hallucinate a fake phone number to save the row. This mathematically forces the drop.

### 4. Explicit Test / Dummy Data Filter
- **Logic**: Developers often leave fake data in databases (e.g., `Test User`, `test@test.com`, `Unknown Customer`).
- **Action**: It selects all string columns using `df.select_dtypes(include=['object', 'string'])`. It builds a Regex pattern: `r'^(test\s*user|test@|unknown\s*customer|dummy\s*data)$'`.
- It loops through the string columns, applying `.str.match(dummy_pattern, na=False)` to build a Boolean mask. Finally, it drops the rows using inverse masking `df_clean[~mask]`.

### 5. Reporting
It maintains a `self.stats` dictionary tracking exactly how many rows were dropped by *which* rule, returning a formatted string in `get_report()` so the UI can display the exact casualties.
