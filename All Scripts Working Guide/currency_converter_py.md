# `cleaning/currency_converter.py` - Financial Standardization

In global datasets, revenue columns are frequently corrupted by mixed currencies. One row might say `$100.50`, another `€50,00`, and a third `£20`.
1. Pandas treats this entire column as an `object` (string) instead of a `float64` (number), making it impossible to calculate averages or sums.
2. The values represent completely different economic weights. 

The `CurrencyConverter` script uses Regex and mathematical scalar conversion to solve both problems.

## Full Working Process & Logic

### 1. Regex Symbol Extraction
- **Method**: It loops through columns marked as `currency` by the `SchemaAgent`.
- **Logic**: It uses a Regular Expression `r'([$€£¥₹])'` to search for currency symbols inside every single string in the column.
- **Action**: It extracts the symbol into a new temporary Pandas Series. It then uses `df[col].str.replace(r'[^\d.]', '', regex=True)` to forcefully delete everything from the string *except* digits and decimal points (stripping out commas, letters, and the symbols themselves).

### 2. The Conversion Mapping
- **The Dictionary**: It contains a hardcoded mapping of Exchange Rates to INR (₹): `{"$": 83.0, "€": 90.0, "£": 105.0, "¥": 0.55}`.
- **Action**: It takes the extracted symbols array and maps it to these multipliers. So a row that had a `€` gets a multiplier of `90.0`. A row that had no symbol gets a default multiplier of `1.0`.

### 3. Type Coercion and Multiplication (Vectorization)
- **Logic**: Now that the original column has been stripped of symbols, it looks like pure strings of numbers (e.g., `"100.50"`).
- **Action**: It forces Pandas to convert the column into mathematics: `pd.to_numeric(df[col], errors='coerce')`. If a string was hopelessly corrupted (e.g., `"One Hundred"`), `errors='coerce'` turns it into `pd.NA` rather than crashing the script.
- Finally, it executes `df[col] = df[col] * multipliers`. This mathematically converts the `$100` into `₹8300` in a single, lightning-fast CPU cycle. The column is now standardized and ready for the `OutlierHandler`.
