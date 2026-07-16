# `cleaning/standardizer.py` - The Semantic Formatter

The `StringCleaner` class handles invisible characters and whitespaces, but it doesn't know *what* a string is. The `Standardizer` class receives the semantic mapping from the `SchemaAgent` (e.g., this column is an `email`, that one is a `name`) and applies strict typographical formatting.

## Full Working Process & Logic

### 1. The Schema Mapping Loop
- **Logic**: It iterates over `self.schema_mapping.items()`. It looks at every column and checks its assigned `SemanticType`.
- **Why**: You cannot apply `.str.title()` to every string column. If you title-case an email address (`John.Doe@Gmail.Com`), it technically becomes invalid because domain specifications often expect lowercase.

### 2. Email Standardization
- **Logic**: If `col_type == SemanticType.EMAIL`:
- **Action**: It executes `df[col].str.lower()`. 
- **Why**: Email addresses are mathematically case-insensitive. Standardizing them to pure lowercase ensures that `john@test.com` and `JOHN@TEST.COM` are viewed as identical strings by the Deduplication Engine later on.

### 3. Name and Location Formatting
- **Logic**: If `col_type in [SemanticType.NAME, SemanticType.LOCATION, SemanticType.CATEGORICAL]`:
- **Action**: It executes `df[col].str.title()`. 
- **Why**: "new york" becomes "New York". "jane doe" becomes "Jane Doe". This is purely for downstream reporting aesthetics and ensuring fuzzy-matching algorithms have a standardized baseline to compare against.

### 4. Phone Number Extraction
- **Problem**: Phone numbers are typed in hundreds of formats: `(555)-123-4567`, `+1 555 123 4567`, `555.123.4567`.
- **Logic**: If `col_type == SemanticType.PHONE_NUMBER`:
- **Action**: It uses Regex: `df[col].str.replace(r'[^\d+]', '', regex=True)`.
- **Why**: This Regex string `[^\d+]` means: "Find anything that is NOT a digit (`\d`) and NOT a plus sign (`+`) and replace it with nothing (`''`)". It instantly deletes all parentheses, dashes, and periods, resulting in a clean, uniform string like `+15551234567`.
