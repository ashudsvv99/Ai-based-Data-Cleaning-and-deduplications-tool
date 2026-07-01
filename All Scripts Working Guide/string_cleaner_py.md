# `cleaning/string_cleaner.py` - The Invisible Bug Killer

When users copy and paste data from websites (like an HTML table), they frequently drag in "invisible" characters. These include trailing spaces, zero-width spaces (`\u200B`), and non-breaking spaces (`\xA0`).
- **The Problem**: To human eyes, `"John"` and `"John "` look identical. But to Python, `"John" == "John "` evaluates to `False`. This breaks grouping, aggregations, and exact-match deduplication.

## Full Working Process & Logic

### 1. Targeting the Right Data Types
- **Logic**: It executes `cols = df.select_dtypes(include=['object', 'string']).columns`.
- **Why**: You cannot run `.str.strip()` on a column filled with integers (`int64`). It will throw an `AttributeError`. Selecting only the string columns prevents the script from crashing when it hits a math column.

### 2. Multi-Pass Sanitization
The script executes three distinct Pandas vectorization passes over the text:

1. **The Unicode Assassin**: 
   - `df[col].str.replace(r'[\u200B-\u200D\uFEFF]', '', regex=True)`
   - **Why**: This targets Zero-Width spaces and Byte Order Marks. These are literal invisible characters that break algorithms without the developer ever seeing why.

2. **The Newline Crusher**:
   - `df[col].str.replace(r'[\r\n\t]+', ' ', regex=True)`
   - **Why**: If a user hit `Enter` inside an Excel cell, it creates a newline `\n`. This converts all tabs and newlines into a single standard space so the data fits on one line.

3. **The Standard Strip**:
   - `df[col].str.strip()`
   - **Why**: Finally, it removes normal spacebar characters from the far left and far right of the string.
