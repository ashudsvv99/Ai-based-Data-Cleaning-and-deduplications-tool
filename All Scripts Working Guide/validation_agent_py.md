# `agents/validation_agent.py` - The Cognitive Auditor

While `validator.py` catches hard math errors (like Negative GST), it cannot catch semantic or logical anomalies. If the `DeduplicationEngine` accidentally merged "John Smith" (a 20-year-old in NY) with "John Smith" (an 80-year-old in LA), the math is fine, but the logic is broken. The `ValidationAgent` acts as a cognitive QA auditor to spot these complex anomalies.

## Full Working Process & Logic

### 1. The Post-Clean Sampling
- **Logic**: We cannot send a 100,000-row cleaned dataset to a local LLM. It would cause a catastrophic Memory Error.
- **Action**: It executes `sample = df.sample(min(num_samples, len(df))).to_dict(orient="records")` (usually 5 rows). 
- **Why**: By converting a random 5-row sample into a Python dictionary, we create a highly compact JSON string that represents the final state of the cleaned data.

### 2. The Audit Prompt
- It loads `prompts/validation.txt`. 
- The prompt instructs the LLM to adopt the persona of a Senior Data Auditor. It asks the LLM to review the sample and explicitly look for:
  - Formatting inconsistencies (e.g., did a string cleaner miss a weird character?).
  - Logical paradoxes (e.g., are the ages realistic? Are the emails valid domains?).
  - Suspicious Imputations (e.g., did an imputation rule fill a column with a value that doesn't make sense contextually?).

### 3. Confidence Scoring
- The LLM is forced to output JSON containing a `"confidence_score"` (0 to 100) and an `"issues"` array.
- **Integration**: The script extracts this score and appends the issues to `metadata["validation_issues"]`. In the Streamlit UI, if this score is below 80%, the "Data Quality" tab renders in yellow/red to warn the user that the AI itself believes the cleaning pipeline might have made a mistake and requires human review.
