# `agents/schema_agent.py` - The Semantic Profiler

Python natively understands data types like `int64` and `object`. But Python doesn't know that an `object` is actually an "Email Address". The `SchemaAgent` acts as the cognitive bridge, applying semantic meaning to every column so downstream tools know how to clean them.

## Full Working Process & Logic

### 1. The Heuristic Pre-Filter
Calling the LLM for all 30 columns of a dataset is slow. We use fast Python regex and logic to guess the obvious ones.
- **Logic**: Iterates over columns and checks the Pandas `dtype`. 
- If `pd.api.types.is_datetime64_any_dtype(df[col])` is true, it instantly classifies it as `date`.
- If the column name contains the word `amount` or `price`, and the data is numeric, it flags it as `currency`.
- If it contains `email` or the string values frequently contain `@`, it flags it as `email`.
- If it cannot guess, it marks the column as `"unknown"`.

### 2. LLM Fallback (Semantic Inference)
If the heuristic marks a column as `"unknown"` (e.g., a column confusingly named `Val1`), we summon the LLM.
- **Sampling**: We don't send the whole column. We run `df[col].dropna().astype(str).head(5).tolist()` to grab 5 random valid samples.
- **Prompting**: We build a prompt passing the column name and the 5 samples. We instruct the LLM to choose from a strict Enum list: `[categorical, text, email, phone_number, currency, numeric, date]`.
- **Action**: The LLM analyzes the semantic structure (e.g., "These numbers look like Zip Codes") and returns a JSON object classifying the column.

### 3. The Central Schema Dictionary
- The final output is a dictionary mapping: `{"Price": "currency", "Email_Address": "email"}`.
- This dictionary is stored in the `PipelineOrchestrator`'s central `metadata`.
- **Why this is critical**: Later, when `standardizer.py` runs, it checks this dictionary. If a column is an `email`, it runs `str.lower()`. Without the `SchemaAgent`, the standardizer would have no idea what logic to apply!
