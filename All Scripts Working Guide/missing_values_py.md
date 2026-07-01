# `cleaning/missing_values.py` - The Smart Imputation Cascade

A typical novice data script fills missing numbers with `0`, and missing strings with `"Unknown"`. That completely destroys the statistical integrity of the data. The `SmartImputer` uses a strict hierarchy to intelligently cascade down and fill in gaps using Numpy statistics and LLM rules.

## Full Working Process & Logic

### 1. The LLM Logic Pass (Dynamic Cross-Column Imputation)
- **Method**: `_apply_logic_rules()`
- **Logic**: The `PlannerAgent` previously generated dynamic JSON rules (e.g., `{"target_column": "Shipping", "condition": "Weight > 100", "fill_value": 500}`). 
- **Action**: The imputer dynamically builds a Pandas query string and evaluates it using `pd.eval(condition)`. If the condition is true for a specific row, it uses `df.loc[mask, target_column] = fill_value`.
- **Why**: This is the most accurate form of imputation because it uses contextual data from *other* columns to deduce the missing value.

### 2. Statistical Fallback - Numerical Handling (Numpy)
If no AI rules apply, the script moves to statistical math.
- **Method**: `_impute_numeric()`
- **Logic**: It calculates the skewness of the column using `df[col].skew()`. Skewness measures the asymmetry of the data distribution.
- **High Skew (`> 1.0` or `< -1.0`)**: If the data is highly skewed (e.g., Income data where 99% of people make $50k, but one guy makes $1B), the average (Mean) will be horribly distorted. In this case, the script mathematically falls back to filling the gaps with the **Median**, because the median is resistant to extreme outliers.
- **Low Skew (Normal Distribution)**: If the data follows a standard bell curve (like Ages or Heights), it fills the gaps with the **Mean** (Average).

### 3. Statistical Fallback - Categorical Handling
- **Method**: `_impute_categorical()`
- **Logic**: You can't calculate the average of a string like "City".
- **Action**: It calculates the `Mode` (the most frequently occurring string) using `df[col].mode()[0]`. It then replaces all `pd.NA` gaps with this dominant value.

### 4. Tracking
Every time `df[col].fillna()` is executed, the script updates a central dictionary tracking exactly how many rows were filled, what method was used (`fill_median`, `fill_mode`), and what the statistical properties (Mean, Max, Min) of the column were. This dictionary is exported to the UI so the user can verify the math.
