# `backend/validator.py` - The Mathematical Constraint Checker

While Artificial Intelligence (`ValidationAgent`) is excellent at spotting semantic weirdness ("Does this name look fake?"), Large Language Models are notoriously terrible at hard mathematics and relational logic. The `BusinessRuleValidator` is a pure Pandas script that executes rigid boolean math checks to catch logic bugs.

## Full Working Process & Logic

### 1. Case-Insensitive Column Mapping
- **Problem**: In a retail dataset, the quantity column might be named `Quantity`, `quantity`, or `QUANTITY`. If we hardcode `df["quantity"] <= 0`, it will throw a `KeyError` and crash the program if the casing doesn't match perfectly.
- **Solution**: The script builds a translation dictionary: `col_map = {c.lower(): c for c in df.columns}`. 
- **Action**: When checking a rule, we look for `"quantity" in col_map`. If it exists, we extract the true column name using `true_col = col_map["quantity"]` and run our math on `df[true_col]`. This entirely prevents KeyErrors.

### 2. Pandas Boolean Masking (Vectorization)
The validator checks thousands of rows in milliseconds using boolean masks.
- **Negative Values**: It applies `mask = pd.to_numeric(df[col], errors="coerce") <= 0`. It counts the `True` values. If `count > 0`, it logs a critical issue: `"Found {count} negative/zero values in '{col}'"`.
- **Relational Logic (Date Checks)**: If it finds both an `order_date` and a `delivery_date` column, it converts both to Pandas Datetime objects using `pd.to_datetime()`. It then runs the mask `mask = df[delivery_col] < df[order_col]`. If it finds a delivery date that happens *before* an order was even placed, it flags it as a logical paradox.

### 3. Aggregation and Logging
Every time a mask returns `> 0` violations, the script appends a formatted string to an `issues` list. This list is injected directly into the final `metadata` dictionary and rendered in the UI with a red warning box, alerting the analyst to manually review those specific mathematical breaks.
